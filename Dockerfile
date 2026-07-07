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

# System dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Install uniocr with PaddleOCR + API deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[paddle,api]"

# Pre-download models on build (optional but recommended for faster cold start)
# RUN python -c "from paddleocr import PaddleOCRVL; PaddleOCRVL(device='cpu')"

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
