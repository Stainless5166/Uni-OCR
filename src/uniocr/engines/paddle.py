import atexit
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .base import BaseOCREngine
from ..models import Document, DocumentPage, Block

logger = logging.getLogger(__name__)

# Module-level reference so we can clean up on exit
_mlx_vlm_process: Optional[subprocess.Popen] = None

_MLX_VLM_DEFAULT_PORT = 8111
_MLX_VLM_DEFAULT_MODEL = "PaddlePaddle/PaddleOCR-VL-1.6"


def _is_port_in_use(port: int) -> bool:
    """Check if a TCP port is already listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _find_free_port(start: int = 8111, end: int = 8200) -> int:
    """Find the first free port in [start, end)."""
    for port in range(start, end):
        if not _is_port_in_use(port):
            return port
    raise RuntimeError(f"No free port found in range {start}-{end}")


def _is_mlx_vlm_installed() -> bool:
    """Check whether mlx-vlm is importable."""
    try:
        import mlx_vlm  # noqa: F401
        return True
    except ImportError:
        return False


def _is_apple_silicon() -> bool:
    """Return True if running on macOS with ARM (Apple Silicon)."""
    try:
        return os.uname().sysname == "Darwin" and os.uname().machine == "arm64"
    except Exception:
        return False


def _ensure_mlx_vlm_server(port: int = _MLX_VLM_DEFAULT_PORT) -> Optional[str]:
    """Auto-start an MLX-VLM server if the environment supports it.

    Decision logic:
      1. If an MLX-VLM server is already running on ``port``, reuse it.
      2. If ``mlx_vlm`` is installed and we're on Apple Silicon, start one.
      3. Otherwise return ``None`` → fall back to plain CPU inference.

    Returns:
        The base URL of the running server (e.g. ``http://localhost:8111/``),
        or ``None`` if MLX-VLM is not available.
    """
    global _mlx_vlm_process

    # 1. Already running? (e.g. user started it manually, or previous call)
    if _is_port_in_use(port):
        logger.info("MLX-VLM server already running on port %d — reusing.", port)
        return f"http://localhost:{port}/"

    # 2. Can we start one?
    if not _is_apple_silicon():
        logger.debug("Not Apple Silicon — MLX-VLM unavailable.")
        return None

    if not _is_mlx_vlm_installed():
        logger.debug("mlx_vlm not installed — skipping auto-start.")
        return None

    # Find a free port (in case default is taken by something else)
    try:
        actual_port = port if not _is_port_in_use(port) else _find_free_port(port + 1)
    except RuntimeError:
        logger.warning("Could not find a free port for MLX-VLM server.")
        return None

    # 3. Launch the server in the background
    logger.info(
        "Auto-starting MLX-VLM server on port %d (Apple Neural Engine acceleration)…",
        actual_port,
    )
    try:
        _mlx_vlm_process = subprocess.Popen(
            [
                sys.executable, "-m", "mlx_vlm.server",
                "--port", str(actual_port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Register cleanup so the server dies when we exit
        atexit.register(_shutdown_mlx_vlm_server)
    except Exception as exc:
        logger.warning("Failed to start MLX-VLM server: %s", exc)
        return None

    # 4. Wait for it to become ready (up to 30 s)
    url = f"http://localhost:{actual_port}/"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if _is_port_in_use(actual_port):
            logger.info("MLX-VLM server is ready at %s", url)
            return url
        time.sleep(0.5)

    logger.warning("MLX-VLM server did not start in time — falling back to CPU.")
    _shutdown_mlx_vlm_server()
    return None


def _shutdown_mlx_vlm_server() -> None:
    """Gracefully terminate the auto-started MLX-VLM server."""
    global _mlx_vlm_process
    if _mlx_vlm_process is not None:
        logger.info("Shutting down auto-started MLX-VLM server (pid %d).", _mlx_vlm_process.pid)
        _mlx_vlm_process.terminate()
        try:
            _mlx_vlm_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mlx_vlm_process.kill()
        _mlx_vlm_process = None


def _cuda_device_available() -> bool:
    """Check whether the installed paddle build can see a working CUDA device."""
    try:
        import paddle
        return bool(paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0)
    except Exception:
        return False


def _resolve_device(explicit: Optional[str]) -> Tuple[str, bool]:
    """Resolve the device to run PaddleOCR-VL on.

    Returns ``(device, was_auto_detected)``. ``was_auto_detected`` tells the
    caller whether it's safe to silently fall back to CPU on failure: an
    explicit request (constructor arg or ``UNIOCR_DEVICE=cpu``/``gpu``) should
    fail loudly instead, since that's a deployment the operator explicitly
    configured and wants to know is broken.
    """
    requested = explicit or os.environ.get("UNIOCR_DEVICE", "auto")
    if requested != "auto":
        return requested, False

    if _cuda_device_available():
        return "gpu", True
    return "cpu", True


# ======================================================================
# Adapter
# ======================================================================


class PaddleOCRVLAdapter(BaseOCREngine):
    """PaddleOCR-VL engine adapter with **automatic** MLX-VLM acceleration.

    On Apple Silicon, this adapter will:
      1. Check if ``mlx_vlm`` is installed.
      2. If yes, auto-start (or reuse) an ``mlx_vlm.server`` process.
      3. Route the VLM inference through Apple Neural Engine for 2-5× speedup.

    No manual configuration needed.  To override, set ``UNIOCR_MLX_VLM_URL``
    or pass ``mlx_vlm_url`` explicitly.
    """

    def __init__(
        self,
        device: Optional[str] = None,
        mlx_vlm_url: Optional[str] = None,
        mlx_vlm_model: Optional[str] = None,
        pipeline_version: str = "v1.6",
    ) -> None:
        self._device, self._device_is_auto = _resolve_device(device)
        self._mlx_vlm_url = mlx_vlm_url or os.environ.get("UNIOCR_MLX_VLM_URL")
        self._mlx_vlm_model = mlx_vlm_model or os.environ.get(
            "UNIOCR_MLX_VLM_MODEL", _MLX_VLM_DEFAULT_MODEL
        )
        self._pipeline_version = pipeline_version
        self._pipeline: Optional[Any] = None  # Lazy-loaded

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _get_pipeline(self) -> Any:
        """Lazy-load the PaddleOCR-VL pipeline on first use."""
        if self._pipeline is not None:
            return self._pipeline

        from paddleocr import PaddleOCRVL

        kwargs: Dict[str, Any] = {
            "device": self._device,
            "pipeline_version": self._pipeline_version,
        }

        # Resolve MLX-VLM URL: explicit → env var → auto-detect & auto-start
        mlx_url = self._mlx_vlm_url
        if mlx_url is None:
            mlx_url = _ensure_mlx_vlm_server()

        if mlx_url:
            logger.info(
                "PaddleOCR-VL → MLX-VLM backend at %s (model: %s)",
                mlx_url,
                self._mlx_vlm_model,
            )
            kwargs.update(
                {
                    "vl_rec_backend": "mlx-vlm-server",
                    "vl_rec_server_url": mlx_url,
                    "vl_rec_api_model_name": self._mlx_vlm_model,
                }
            )
        else:
            logger.info(
                "PaddleOCR-VL running with device=%s. "
                "Install mlx-vlm for automatic Apple Neural Engine acceleration.",
                self._device,
            )

        logger.info("Loading PaddleOCR-VL pipeline (device=%s)…", self._device)
        try:
            self._pipeline = PaddleOCRVL(**kwargs)
        except Exception:
            # Only auto-detected devices get a silent fallback - an explicit
            # UNIOCR_DEVICE=gpu (or constructor arg) should fail loudly, since
            # that's a deployment the operator configured and needs to see is
            # broken, not something to paper over.
            if not self._device_is_auto or self._device == "cpu":
                raise
            logger.warning(
                "PaddleOCR-VL pipeline failed to load on auto-detected device=%s; "
                "falling back to CPU.",
                self._device,
                exc_info=True,
            )
            self._device = "cpu"
            kwargs["device"] = "cpu"
            self._pipeline = PaddleOCRVL(**kwargs)
        return self._pipeline

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------

    def extract(self, input_source: Union[str, Path], **kwargs: Any) -> Document:
        input_path = Path(input_source)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        pipeline = self._get_pipeline()
        results_generator = pipeline.predict(input=str(input_path))

        pages: List[DocumentPage] = []
        for page_idx, res in enumerate(results_generator):
            blocks = self._parse_blocks(res)

            # PaddleOCRVLResult.markdown is a dict with 'markdown_texts' key
            page_md = ""
            try:
                md_data = res.markdown
                if isinstance(md_data, dict):
                    page_md = md_data.get("markdown_texts", "")
                elif isinstance(md_data, str):
                    page_md = md_data
            except Exception:
                pass

            # Build text from blocks; fall back to markdown content
            page_text = "\n".join(b.text for b in blocks)
            if not page_text and page_md:
                page_text = re.sub(r"[#*_`>|]", "", page_md).strip()
            if not page_md:
                page_md = "\n\n".join(b.text for b in blocks)

            pages.append(
                DocumentPage(
                    page_number=page_idx + 1,
                    blocks=blocks,
                    text=page_text,
                    markdown=page_md,
                )
            )

        return Document(pages=pages)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_blocks(res: Any) -> List[Block]:
        """Extract standardised Block objects from a PaddleOCR result.

        PaddleOCRVLResult is a dict subclass; the core data lives under
        ``res['res']['parsing_res_list']``.
        """
        try:
            inner = res["res"]
            parsed_res = inner.get("parsing_res_list", [])
        except (KeyError, TypeError):
            parsed_res = []

        blocks: List[Block] = []
        for item in parsed_res:
            raw_bbox = item.get("block_bbox", (0, 0, 0, 0))
            blocks.append(
                Block(
                    block_type=item.get("block_label", "text"),
                    text=item.get("block_content", ""),
                    bbox=tuple(float(v) for v in raw_bbox),
                    confidence=1.0,
                    extra_data=item,
                )
            )
        return blocks
