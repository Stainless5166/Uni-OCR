FROM python:3.10-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Install uniocr with PaddleOCR + API deps
RUN pip install --no-cache-dir ".[paddle,api]"

# Pre-download models on build (optional but recommended for faster cold start)
# RUN python -c "from paddleocr import PaddleOCRVL; PaddleOCRVL(device='cpu')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["uniocr"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
