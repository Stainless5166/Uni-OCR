<p align="center">
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/logo.svg" alt="UniOCR Logo" width="400"/>
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

## ✨ Key Features

<div align="center">
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/dashboard.png" alt="UniOCR Web Dashboard" width="80%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br/><br/>
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/settings.png" alt="UniOCR Hardware Radar" width="80%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
</div>

- 🖥️ **Stunning Enterprise Dashboard** — A fully re-engineered Glassmorphism Web UI featuring an interactive OCR playground, API generator, and live system monitoring.
- 📊 **Geek-Level Hardware Radar** — Real-time backend polling of physical sensor data: CPU/GPU frequencies, RAM/Swap allocation, Apple Neural Engine status, and active AI model library versions.
- 🔐 **Military-Grade Security** — Built-in local SQLite persistence. Full support for 2FA (TOTP), Admin master passwords, and one-click toggles between public/private API access.
- 🔑 **Seamless API Key Management** — Issue and revoke API Tokens directly from the UI, with auto-generated ready-to-use `curl` snippets for instant integration testing.
- 🔌 **Pluggable Engines** — PaddleOCR-VL (deep document AI) and Apple Vision (native macOS) with automatic priority fallback.
- ⚡ **Zero-Config Acceleration** — Auto-detects Apple Silicon → launches MLX-VLM → offloads to Neural Engine (NPU).
- 🚀 **Zero-Delay Smart Cache (LRU)** — Instantaneous format switching (TXT, JSON, MD, PDF download/preview) for recent files without re-running the neural network.
- 🐳 **Docker Ready** — Single-command deployment via Docker Compose for production-grade frontend & backend.

## 🚀 Quick Start

### Option 1: pip install

```bash
# Core only (lightweight)
pip install uniocr

# With PaddleOCR-VL (powerful document AI, ~1.8 GB model download on first run)
pip install "uniocr[paddle]"

# With Apple Vision (macOS only, uses built-in system OCR)
pip install "uniocr[apple]"

# Everything (Recommended for Dashboard & API)
pip install "uniocr[all]"
```

### Option 2: Docker (recommended for servers)

```bash
# Use Docker Compose (pulls and runs all components instantly)
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
```

### CLI

```bash
# Start the full Web UI Console & API server
uniocr serve --port 8000

# Extract text (outputs Markdown by default)
uniocr extract document.pdf -o result.md

# Generate a Searchable PDF
uniocr extract input_image.jpg -o output_searchable.pdf
```

### REST API & Dashboard Console

Start the server:

```bash
uniocr serve --port 8000
```
- **Web UI Console**: `http://localhost:8000/`
- **System Settings & Radar**: `http://localhost:8000/settings`
- **Interactive API Docs**: `http://localhost:8000/docs`

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check & engine list |
| `GET` | `/engines` | List OCR engines available in this environment |
| `POST` | `/extract` | Extract text from an uploaded file (JSON/Markdown) |
| `POST` | `/extract/url` | Extract text from a URL |
| `POST` | `/extract/base64` | Extract text from a Base64-encoded payload (JSON) |
| `POST` | `/extract/batch` | Extract text from multiple uploaded files in one request |
| `POST` | `/extract/pdf` | Extract text and return a Searchable PDF file |

*(If Public API Access is disabled, these endpoints require an `Authorization: Bearer <API_KEY>` header).*

## 🐳 Docker Build

```bash
git clone https://github.com/yuanweize/uni-ocr.git
cd uni-ocr
docker compose up -d --build
```

By default `docker-compose.yml` only binds the API to `127.0.0.1` (override `UNIOCR_BIND_HOST`, e.g. a Tailscale IP, for LAN/remote access). The SQLite database (admin credentials, API keys, JWT secret) persists in a named volume across restarts.

> **First boot**: the image ships with `admin`/`admin` and Public API Access enabled. Log in at `/settings` immediately, set a real password, and turn off public access if you don't want unauthenticated extraction.

### Optional build variants

```bash
# GPU build — needs a matching CUDA driver + the NVIDIA Container Toolkit on
# the host. Pick a cuXXX tag at or below `nvidia-smi`'s reported CUDA version.
docker build \
  --build-arg PADDLE_PACKAGE=paddlepaddle-gpu==3.3.0 \
  --build-arg PADDLE_INDEX_URL=https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  -t uniocr:gpu .

# Pre-download the ~1.8GB PaddleOCR-VL model at build time instead of on
# first request — useful for network-isolated deployments.
docker build --build-arg PREDOWNLOAD_MODELS=true -t uniocr:offline-ready .
```

## 🔧 Engine Priority

| Priority | Engine | Best for | Speed |
|----------|--------|----------|-------|
| 1 | **PaddleOCR-VL** + MLX-VLM | Complex layouts, tables, formulas, 109 languages | ⚡⚡ |
| 2 | **PaddleOCR-VL** (CPU) | Same capabilities, without MLX acceleration | ⚡ |
| 3 | **Apple Vision** | Simple text, macOS only, instant | ⚡⚡⚡ |

> **Apple Silicon users**: when `mlx-vlm` is installed, UniOCR automatically starts an MLX-VLM server for Neural Engine acceleration. No configuration needed.

## 📄 License

[MIT](LICENSE) © 2026 Weize Yuan
