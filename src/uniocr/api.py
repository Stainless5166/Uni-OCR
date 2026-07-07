"""UniOCR FastAPI service — production-ready REST API.

Start with::

    uniocr serve --port 8000

Or directly::

    uvicorn uniocr.api:app --host 0.0.0.0 --port 8000 --workers 4
"""

import base64
import logging
import uuid
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List

# Suppress annoying third-party paddlex warnings
warnings.filterwarnings("ignore", message=".*'mlx-vlm-server' does not support.*")

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

from . import UniOCR, list_available_engines
from .models import Document
from .exporters.pdf import export_to_pdf
from .routers_auth import router as auth_router, verify_public_or_authenticated
from .routers_system import router as system_router
from .routers_stream import router as stream_router
from .cache import ocr_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UniOCR API",
    description=(
        "Unified multilingual OCR service.\n\n"
        "Upload images or PDFs and receive structured text, Markdown, "
        "and layout blocks in a single JSON response."
    ),
    version="3.1.1",
    docs_url=None,
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(stream_router)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    from fastapi.responses import HTMLResponse
    
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_ui_parameters={"syntaxHighlight.theme": "monokai", "defaultModelsExpandDepth": -1},
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    )
    
    custom_css = """
    <style>
        body { background: #1a1a2e; }
        .swagger-ui .topbar { background: #16213e; }
        .swagger-ui .info .title { color: #e0e0e0; }
        .swagger-ui .info p, .swagger-ui .info li { color: #b0b0b0; }
        .swagger-ui .scheme-container { background: #16213e; box-shadow: none; }
        .swagger-ui .opblock-tag { color: #e0e0e0; border-bottom-color: #333; }
        .swagger-ui .opblock .opblock-summary-description { color: #999; }
        .swagger-ui .opblock .opblock-section-header { background: rgba(0,0,0,0.2); }
        .swagger-ui .opblock .opblock-section-header h4 { color: #ccc; }
        .swagger-ui .model-box, .swagger-ui section.models { background: #16213e; }
        .swagger-ui .model { color: #ccc; }
        .swagger-ui table thead tr th { color: #ccc; border-bottom-color: #444; }
        .swagger-ui .parameter__name { color: #e0e0e0; }
        .swagger-ui .parameter__type { color: #999; }
        .swagger-ui input[type=text], .swagger-ui textarea, .swagger-ui select {
            background: #2a2a4a; color: #e0e0e0; border-color: #444;
        }
        .swagger-ui .btn { border-color: #555; color: #ccc; }
        .swagger-ui .response-col_status { color: #e0e0e0; }
        .swagger-ui .response-col_description p { color: #999; }
        .swagger-ui .markdown p, .swagger-ui .markdown pre { color: #b0b0b0; }
        
        /* Fix text contrast for endpoint paths on dark backgrounds */
        .swagger-ui .opblock .opblock-summary-path,
        .swagger-ui .opblock .opblock-summary-path a { color: #fff !important; font-weight: bold; }
        .swagger-ui .opblock.opblock-get .opblock-summary-path a { color: #8ce1ff !important; }
        .swagger-ui .opblock.opblock-post .opblock-summary-path a { color: #8cf2b8 !important; }
        .swagger-ui .opblock.opblock-delete .opblock-summary-path a { color: #ff8c8c !important; }
    </style>
    """
    
    # Inject the custom CSS right before the closing </head> tag
    html_content = response.body.decode("utf-8")
    html_content = html_content.replace("</head>", f"{custom_css}\n</head>")
    return HTMLResponse(html_content)

# ---------------------------------------------------------------------------
# Standardised Error Handling (RFC 7807)
# ---------------------------------------------------------------------------


def _problem_details(
    status_code: int, title: str, detail: str, **kwargs: Any
) -> JSONResponse:
    content = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "request_id": str(uuid.uuid4()),
        **kwargs,
    }
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _problem_details(
        status_code=exc.status_code,
        title="HTTP Error",
        detail=exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _problem_details(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Validation Error",
        detail="The request payload is invalid.",
        errors=exc.errors(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return _problem_details(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail=str(exc),
    )


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    version: str = Field(..., example="0.2.2")
    engines: List[str] = Field(..., example=["paddle", "apple"])
    details: Dict[str, Any] = Field(..., description="Deep check results for each engine")


class ExtractBase64Request(BaseModel):
    base64_data: str = Field(
        ...,
        description="Base64 encoded file content. May include data URI scheme.",
    )
    engine: str = Field("auto", description="Engine: auto | paddle | apple")


class BatchResult(BaseModel):
    request_id: str
    file_count: int
    results: List[Dict[str, Any]]
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Engine pool & helpers
# ---------------------------------------------------------------------------

_ocr_pool: Dict[str, UniOCR] = {}


def _get_ocr(engine: str = "auto") -> UniOCR:
    if engine not in _ocr_pool:
        logger.info("Initialising OCR engine pool entry: %s", engine)
        _ocr_pool[engine] = UniOCR(engine=engine)
    return _ocr_pool[engine]


def _build_response(doc: Document, elapsed: float) -> Dict[str, Any]:
    """Build a standardised API response envelope."""
    result = doc.to_dict()
    result["elapsed_seconds"] = elapsed
    result["request_id"] = str(uuid.uuid4())
    return result


def _decode_base64_to_temp(b64_str: str) -> Path:
    """Decodes a base64 string to a temporary file, guessing extension by magic bytes."""
    # Strip data URI scheme if present
    if "," in b64_str:
        _, b64_str = b64_str.split(",", 1)

    try:
        data = base64.b64decode(b64_str)
    except Exception as e:
        raise ValueError(f"Invalid Base64 data: {e}")

    # Magic byte detection
    ext = ".bin"
    if data.startswith(b"%PDF"):
        ext = ".pdf"
    elif data.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> Any:
    """Deep health / readiness probe."""
    engines = list_available_engines()
    details: Dict[str, Any] = {}

    for eng in engines:
        try:
            adapter = _get_ocr(eng).engine
            details[eng] = {"available": adapter.is_available()}
        except Exception as e:
            details[eng] = {"available": False, "error": str(e)}

    return {
        "status": "ok",
        "version": app.version,
        "engines": engines,
        "details": details,
    }


@app.get("/engines", tags=["System"])
async def engines() -> Dict[str, Any]:
    """List OCR engines available in the current environment."""
    return {"available_engines": list_available_engines()}


@app.post("/extract", tags=["OCR"], dependencies=[Depends(verify_public_or_authenticated)])
async def extract_file(
    file: UploadFile = File(..., description="Image or PDF file to process"),
    engine: str = Form("auto", description="Engine: auto | paddle | apple"),
) -> JSONResponse:
    """Extract text and layout from an uploaded file (multipart/form-data)."""
    start = time.monotonic()

    suffix = Path(file.filename or "upload").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        ocr = _get_ocr(engine)
        doc = ocr.extract(tmp_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    elapsed = round(time.monotonic() - start, 3)
    return JSONResponse(content=_build_response(doc, elapsed))


@app.post("/extract/url", tags=["OCR"], dependencies=[Depends(verify_public_or_authenticated)])
async def extract_url(
    url: str = Form(..., description="Public URL of an image or PDF"),
    engine: str = Form("auto", description="Engine: auto | paddle | apple"),
) -> JSONResponse:
    """Extract text and layout from a URL pointing to an image or PDF."""
    start = time.monotonic()

    try:
        ocr = _get_ocr(engine)
        doc = ocr.extract(url)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = round(time.monotonic() - start, 3)
    return JSONResponse(content=_build_response(doc, elapsed))


@app.post("/extract/base64", tags=["OCR"], dependencies=[Depends(verify_public_or_authenticated)])
async def extract_base64(req: ExtractBase64Request) -> JSONResponse:
    """Extract text and layout from a Base64-encoded string (application/json).
    
    Automatically detects PDF or image based on magic bytes.
    Perfect for n8n, Dify, and AI Agents that prefer JSON payloads.
    """
    start = time.monotonic()
    tmp_path = None

    try:
        tmp_path = _decode_base64_to_temp(req.base64_data)
        ocr = _get_ocr(req.engine)
        doc = ocr.extract(tmp_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    elapsed = round(time.monotonic() - start, 3)
    return JSONResponse(content=_build_response(doc, elapsed))


@app.post("/extract/batch", response_model=BatchResult, tags=["OCR"], dependencies=[Depends(verify_public_or_authenticated)])
async def extract_batch(
    files: List[UploadFile] = File(..., description="Multiple files to process"),
    engine: str = Form("auto"),
) -> Any:
    """Process multiple files in one request (sequential)."""
    start = time.monotonic()
    ocr = _get_ocr(engine)
    results: List[Dict[str, Any]] = []

    for file in files:
        suffix = Path(file.filename or "upload").suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            if not content:
                results.append({"filename": file.filename, "error": "Empty file"})
                continue
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            doc = ocr.extract(tmp_path)
            item = doc.to_dict()
            item["filename"] = file.filename
            results.append(item)
        except Exception as exc:
            logger.warning("Error processing %s: %s", file.filename, exc)
            results.append({"filename": file.filename, "error": str(exc)})
        finally:
            tmp_path.unlink(missing_ok=True)

    elapsed = round(time.monotonic() - start, 3)
    return {
        "request_id": str(uuid.uuid4()),
        "file_count": len(files),
        "results": results,
        "elapsed_seconds": elapsed,
    }


@app.post("/extract/pdf", response_class=FileResponse, tags=["OCR"], dependencies=[Depends(verify_public_or_authenticated)])
async def extract_to_pdf(
    file: UploadFile = File(..., description="Image or PDF file to process"),
    engine: str = Form("auto", description="Engine: auto | paddle | apple"),
) -> Any:
    """Extract text and layout, returning a Searchable PDF (双层 PDF)."""
    suffix = Path(file.filename or "upload").suffix or ".png"
    
    # We need two temporary files: one for input, one for output
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await file.read()
    if not content:
        tmp_in.close()
        Path(tmp_in.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
        
    tmp_in.write(content)
    tmp_in.close()
    in_path = Path(tmp_in.name)
    
    out_path = Path(tempfile.mktemp(suffix=".pdf"))
    
    try:
        doc = ocr_cache.get_or_extract(engine, content)
        export_to_pdf(doc, in_path, out_path)
    except Exception as exc:
        in_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))
        
    # Cleanup task for background
    def cleanup():
        in_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
        
    return FileResponse(
        path=out_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
        background=BackgroundTask(cleanup),
    )

# ---------------------------------------------------------------------------
# SPA Static Files Fallback
# ---------------------------------------------------------------------------
frontend_dist = Path(__file__).parent / "static"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Resolve and confirm the target stays within frontend_dist to prevent
        # path traversal (e.g. "../../data/uniocr.db") from escaping the static root.
        static_root = frontend_dist.resolve()
        target_file = (static_root / full_path).resolve()
        if target_file.is_relative_to(static_root) and target_file.is_file():
            return FileResponse(target_file)
        # Fallback to index.html for SPA routing
        return FileResponse(static_root / "index.html")
