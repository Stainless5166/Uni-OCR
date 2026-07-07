# ---------------------------------------------------------------------------
# Build stage — installs uniocr and its (large) OCR dependencies into an
# isolated prefix so none of the build tooling or intermediate pip state
# ends up in the image that actually ships.
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS builder

WORKDIR /app

# build-essential is a safety net for any optional dependency that doesn't
# publish a prebuilt wheel for this platform/Python version. It never
# reaches the final image, so keeping it here costs nothing at runtime.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Override these to build a GPU image instead, e.g.:
#   --build-arg PADDLE_PACKAGE=paddlepaddle-gpu==3.3.0
#   --build-arg PADDLE_INDEX_URL=https://www.paddlepaddle.org.cn/packages/stable/cu126/
# (pick the cuXXX tag at or below what `nvidia-smi` reports as the driver's
# max supported CUDA version). The GPU wheel bundles its own CUDA/cuDNN/NCCL,
# so no system CUDA toolkit is added to the image — only a host-side NVIDIA
# driver + the NVIDIA Container Toolkit (for device passthrough at runtime)
# are required. Defaults below reproduce the plain CPU build.
ARG PADDLE_PACKAGE="paddlepaddle>=3.2.1"
ARG PADDLE_INDEX_URL=

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install \
        ${PADDLE_INDEX_URL:+--index-url ${PADDLE_INDEX_URL} --extra-index-url https://pypi.org/simple} \
        "${PADDLE_PACKAGE}" && \
    pip install --no-cache-dir --prefix=/install "paddleocr[doc-parser]>=3.0.0" ".[api]"

# ---------------------------------------------------------------------------
# Runtime stage — same base (paddlepaddle only ships glibc/manylinux wheels,
# so Alpine/musl isn't viable here), but with no compiler, no pip cache, and
# no leftover apt metadata: just the installed packages and runtime libs.
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS base

# Don't write .pyc files or buffer stdout/stderr — also keeps a read-only
# rootfs viable since /app never needs a __pycache__ write.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Auto-link GHCR package to GitHub repository
LABEL org.opencontainers.image.source=https://github.com/yuanweize/uni-ocr

# Non-root runtime user. Give it a real home directory since PaddleX/model
# caches resolve under $HOME by default.
RUN groupadd --gid 1000 uniocr && \
    useradd --uid 1000 --gid uniocr --create-home --shell /usr/sbin/nologin uniocr

# Runtime shared libs only (no compiler toolchain in this stage)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# App-writable paths: the SQLite DB under ./data and the non-root user's home
# (model/cache downloads). Everything else can stay owned by root.
RUN mkdir -p /app/data && \
    chown -R uniocr:uniocr /app/data /home/uniocr

USER uniocr
ENV HOME=/home/uniocr

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["uniocr"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
