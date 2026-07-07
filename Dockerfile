# ---------------------------------------------------------------------------
# Build stage — installs uniocr and its (large) OCR dependencies into an
# isolated prefix so none of the build tooling or intermediate pip state
# ends up in the image that actually ships.
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS builder

WORKDIR /app

# build-essential is a safety net for any optional dependency that doesn't
# publish a prebuilt wheel for this platform/Python version. libgl1 etc. are
# needed here too (not just in the runtime stage) because the optional
# PREDOWNLOAD_MODELS step below actually imports cv2/paddleocr in this
# stage, which dlopen()s libGL at import time. None of this reaches the
# final image either way.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 libgomp1 && \
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

# Optionally pre-download the PaddleOCR-VL model weights (~1.8GB) at build
# time instead of on first request, so a container running on a
# network-isolated Docker network (e.g. compose `internal: true`) can still
# serve its first request. Off by default since it adds ~1.8GB to every
# build; enable with --build-arg PREDOWNLOAD_MODELS=true. The `mkdir -p`
# keeps the COPY in the runtime stage below valid either way.
#
# This always uses a throwaway plain-CPU paddle install to do the actual
# downloading, regardless of PADDLE_PACKAGE. paddlepaddle-gpu's compiled
# core (libpaddle.so) unconditionally dlopen()s libcuda.so.1 the moment
# `paddle` is imported — that's the NVIDIA *driver's* library, not
# something the pip wheel bundles, and a `docker build` environment has no
# GPU/driver access at all, so this fails before device='cpu' even matters.
# The plain CPU wheel has no such dependency. The downloaded weight files
# are identical either way — see the note on the real install above.
ARG PREDOWNLOAD_MODELS=false
RUN mkdir -p /root/.paddlex && \
    if [ "$PREDOWNLOAD_MODELS" = "true" ]; then \
        pip install --no-cache-dir --prefix=/predl "paddlepaddle>=3.2.1" "paddleocr[doc-parser]>=3.0.0" && \
        PYTHONPATH=/predl/lib/python3.10/site-packages python -c \
            "from paddleocr import PaddleOCRVL; PaddleOCRVL(device='cpu', pipeline_version='v1.6')"; \
    fi

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

# Runtime shared libs only (no compiler toolchain in this stage). libgomp1
# is needed by paddlepaddle's compiled OpenMP-parallelized ops at inference
# time, not just at import — a plain `import paddle` won't surface its
# absence, only an actual extract request does.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

# Carries over the pre-downloaded model cache when PREDOWNLOAD_MODELS=true
# was set at build time; otherwise this is just an empty directory and the
# app downloads models on first use as before.
COPY --from=builder --chown=uniocr:uniocr /root/.paddlex /home/uniocr/.paddlex

# App-writable path for the SQLite DB. /home/uniocr is already owned by
# uniocr (created via useradd --create-home, plus --chown above).
RUN mkdir -p /app/data && \
    chown uniocr:uniocr /app/data

USER uniocr
ENV HOME=/home/uniocr

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["uniocr"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
