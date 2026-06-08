<p align="center">
  <img src="assets/logo.svg" alt="UniOCR Logo" width="400"/>
</p>

<p align="center">
  <strong>One API. Multiple engines. Zero friction.</strong>
</p>

<p align="center">
  <a href="https://github.com/yuanweize/uni-ocr/actions"><img src="https://img.shields.io/github/actions/workflow/status/yuanweize/uni-ocr/ci.yml?style=flat-square&logo=github" alt="CI"></a>
  <a href="https://pypi.org/project/uniocr/"><img src="https://img.shields.io/pypi/v/uniocr?style=flat-square&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://github.com/yuanweize/uni-ocr/pkgs/container/uni-ocr"><img src="https://img.shields.io/badge/GHCR-Docker-blue?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="README_zh.md"><img src="https://img.shields.io/badge/文档-中文版-orange?style=flat-square" alt="中文文档"></a>
</p>

---

**UniOCR** is a unified, multilingual OCR abstraction layer that wraps best-in-class OCR engines behind a single, clean interface. Throw any image or PDF at it — get back structured text, Markdown, and layout blocks — regardless of which engine runs under the hood.

Built for developers, AI agents, and automation pipelines (n8n, Dify, Telegram bots, etc.).

## ✨ Highlights

- 🔌 **Pluggable engines** — PaddleOCR-VL (deep document AI) and Apple Vision (native macOS) with automatic priority fallback
- ⚡ **Zero-config acceleration** — Auto-detects Apple Silicon → launches MLX-VLM → Neural Engine speedup. No manual setup.
- 📄 **Accepts anything** — file paths, URLs, Base64 data URIs, multi-page PDFs (auto-flattened)
- 📦 **Unified output** — `Document → Pages → Blocks` with `.text`, `.markdown`, `.to_dict()`
- 🌐 **REST API** — FastAPI with Swagger docs, batch processing, request tracking — ready for n8n / Dify / any HTTP client
- 🐳 **Docker ready** — single command deployment via Docker Compose
- 🖥️ **CLI** — `uniocr extract`, `uniocr engines`, `uniocr serve`

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    User Interface Layer                       │
│              SDK  ·  CLI  ·  REST API                        │
├──────────────────────────────────────────────────────────────┤
│                    Input Processor                           │
│         URL → File  ·  PDF → Images  ·  Base64 → File       │
├──────────────────────────────────────────────────────────────┤
│                Engine Dispatcher (auto)                      │
│         PaddleOCR-VL → Apple Vision → fallback               │
├─────────────────────┬────────────────────────────────────────┤
│   PaddleOCR-VL      │        Apple Vision                    │
│   + MLX-VLM         │        (native macOS)                  │
│   (auto-accelerated)│                                        │
├─────────────────────┴────────────────────────────────────────┤
│                 Standardised Output                          │
│          Document → Pages → Blocks                           │
│          .text  ·  .markdown  ·  .to_dict()                  │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: pip install

```bash
# Core only (lightweight, includes PDF flattening)
pip install uniocr

# With PaddleOCR-VL (powerful document AI, ~1.8 GB model download on first run)
pip install "uniocr[paddle]"

# With Apple Vision (macOS only, uses built-in system OCR)
pip install "uniocr[apple]"

# With REST API server
pip install "uniocr[api]"

# Everything
pip install "uniocr[all]"
```

### Option 2: Docker (recommended for servers)

```bash
# Quick start — pull and run in detached mode
docker run -d --name uniocr -p 8000:8000 ghcr.io/yuanweize/uni-ocr:latest

# Or use Docker Compose (recommended)
curl -O https://raw.githubusercontent.com/yuanweize/uni-ocr/master/docker-compose.yml
docker compose up -d

# Check it's running
curl http://localhost:8000/health
```

## 📖 Usage

### Python SDK

```python
from uniocr import UniOCR

ocr = UniOCR(engine="auto")          # Auto-selects best available engine
doc = ocr.extract("invoice.pdf")

print(doc.text)                       # Plain text
print(doc.markdown)                   # Structured Markdown
print(doc.to_dict())                  # JSON-serialisable dict

# Access individual blocks with layout info
for page in doc.pages:
    for block in page.blocks:
        print(f"[{block.block_type}] {block.text}")
        print(f"  bbox: {block.bbox}, confidence: {block.confidence}")
```

### CLI

```bash
# List available engines
uniocr engines
# Output:
#   Available engines:
#     • paddle
#     • apple

# Extract text (default: Markdown output to stdout)
uniocr extract document.pdf

# Specify engine, format, and output file
uniocr extract scan.png --engine apple --format json -o result.json

# Extract from a URL
uniocr extract "https://example.com/receipt.png" --format text

# Start the API server (single worker)
uniocr serve --port 8000

# Production: multiple workers
uniocr serve --port 8000 --workers 4
```

### REST API

Start the server:

```bash
uniocr serve --port 8000
# Or via Docker:
docker compose up -d
```

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (includes engine list) |
| `GET` | `/engines` | List available OCR engines |
| `GET` | `/docs` | Interactive Swagger UI |
| `POST` | `/extract` | Extract from uploaded file |
| `POST` | `/extract/url` | Extract from a public URL |
| `POST` | `/extract/batch` | Batch process multiple files |

#### Examples

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"ok","version":"0.2.1","engines":["paddle","apple"]}

# Upload a file
curl -X POST http://localhost:8000/extract \
  -F "file=@invoice.pdf" \
  -F "engine=auto"

# Extract from URL
curl -X POST http://localhost:8000/extract/url \
  -F "url=https://example.com/scan.png" \
  -F "engine=apple"

# Batch processing (multiple files in one request)
curl -X POST http://localhost:8000/extract/batch \
  -F "files=@page1.png" \
  -F "files=@page2.png" \
  -F "engine=auto"
```

#### Response format

```json
{
  "request_id": "ab07767c-331f-4f26-be01-2fcb75d36149",
  "engine": "PaddleOCRVLAdapter",
  "page_count": 1,
  "text": "Invoice #12345\nTotal: €1,234.56",
  "markdown": "# Invoice #12345\n\nTotal: €1,234.56",
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "markdown": "...",
      "blocks": [
        {
          "block_type": "text",
          "text": "Invoice #12345",
          "bbox": [0.05, 0.02, 0.45, 0.06],
          "confidence": 0.98
        }
      ]
    }
  ],
  "elapsed_seconds": 2.35
}
```

## 🐳 Docker

### Quick Run

```bash
# Run in background (detached mode)
docker run -d \
  --name uniocr \
  -p 8000:8000 \
  -v uniocr-models:/root/.paddlex \
  ghcr.io/yuanweize/uni-ocr:latest
```

### Docker Compose (recommended)

```bash
# Download compose file
curl -O https://raw.githubusercontent.com/yuanweize/uni-ocr/master/docker-compose.yml

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Build locally

```bash
git clone https://github.com/yuanweize/uni-ocr.git
cd uni-ocr
docker compose up -d --build
```

## 🔧 Engine Priority

When `engine="auto"`, UniOCR selects the best available engine:

| Priority | Engine | Best for | Speed |
|----------|--------|----------|-------|
| 1 | **PaddleOCR-VL** + MLX-VLM | Complex layouts, tables, formulas, 109 languages | ⚡⚡ |
| 2 | **PaddleOCR-VL** (CPU) | Same capabilities, without MLX acceleration | ⚡ |
| 3 | **Apple Vision** | Simple text, macOS only, instant | ⚡⚡⚡ |

> **Apple Silicon users**: when `mlx-vlm` is installed, UniOCR automatically starts an MLX-VLM server for Neural Engine acceleration. No configuration needed. The server is cleaned up on exit.

## 🔗 Integration Examples

UniOCR is designed to be called by automation tools and AI agents.

### n8n Workflow

Use the **HTTP Request** node to call UniOCR:

```
Telegram Trigger → HTTP Request (UniOCR /extract) → AI Agent → ERPNext API
```

Configuration:
- **Method**: `POST`
- **URL**: `http://uniocr:8000/extract`
- **Body**: Form-Data, `file` = `{{ $binary.data }}`

### Dify Tool

Add UniOCR as a custom tool in Dify with the OpenAPI spec at `/docs`.

### Bob (macOS OCR Plugin)

UniOCR can serve as the OCR backend for [Bob](https://bobtranslate.com/):

```bash
# Start UniOCR on the default port
uniocr serve --port 8000
# Bob → Preferences → OCR → Custom API → http://localhost:8000/extract
```

### Shell / Scripts

```bash
# Quick OCR from clipboard image (macOS)
pbpaste | base64 | curl -s -X POST http://localhost:8000/extract \
  -F "file=@-;filename=clipboard.png" | jq .text
```

## ⚙️ Configuration

UniOCR works out of the box with zero configuration. For advanced use cases:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `UNIOCR_PORT` | API server port (Docker Compose) | `8000` |
| `UNIOCR_MLX_VLM_URL` | Override MLX-VLM server URL | Auto-detected |
| `UNIOCR_MLX_VLM_MODEL` | MLX-VLM model identifier | `PaddlePaddle/PaddleOCR-VL-1.6` |

Copy `.env.example` to `.env` to customise:

```bash
cp .env.example .env
```

## 📁 Project Structure

```
uni-ocr/
├── src/uniocr/
│   ├── __init__.py          # UniOCR main class & public API
│   ├── models.py            # Document / Page / Block dataclasses
│   ├── cli.py               # CLI: extract · engines · serve
│   ├── api.py               # FastAPI REST service
│   ├── engines/
│   │   ├── __init__.py      # Engine registry & auto-dispatcher
│   │   ├── base.py          # BaseOCREngine ABC
│   │   ├── apple_vision.py  # macOS Vision adapter
│   │   └── paddle.py        # PaddleOCR-VL + MLX-VLM adapter
│   └── processors/
│       └── input.py         # URL / Base64 / PDF normalisation
├── assets/
│   └── logo.svg             # Project logo
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── CLAUDE.md                # Development guidelines
├── LICENSE                  # MIT
├── README.md                # English docs (this file)
└── README_zh.md             # 中文文档
```

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request.

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## 📄 License

[MIT](LICENSE) © 2026 Weize Yuan
