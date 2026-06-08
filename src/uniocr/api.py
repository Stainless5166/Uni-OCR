"""UniOCR FastAPI service — production-ready REST API.

Start with::

    uniocr serve --port 8000

Or directly::

    uvicorn uniocr.api:app --host 0.0.0.0 --port 8000 --workers 4
"""

import base64
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import UniOCR, list_available_engines
from .models import Document

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
    version="0.2.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    version: str = Field(..., example="0.2.1")
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
            adapter = UniOCR(engine=eng).engine
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


@app.post("/extract", tags=["OCR"])
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


@app.post("/extract/url", tags=["OCR"])
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


@app.post("/extract/base64", tags=["OCR"])
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


@app.post("/extract/batch", response_model=BatchResult, tags=["OCR"])
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
