<p align="center">
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/logo.svg" alt="UniOCR Logo" width="400"/>
</p>

<p align="center">
  <strong>一套接口，多引擎驱动，零摩擦使用。</strong>
</p>

<p align="center">
  <a href="https://github.com/yuanweize/uni-ocr/actions"><img src="https://img.shields.io/github/actions/workflow/status/yuanweize/uni-ocr/ci.yml?style=flat-square&logo=github" alt="CI"></a>
  <a href="https://pypi.org/project/uniocr/"><img src="https://img.shields.io/pypi/v/uniocr?style=flat-square&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://github.com/yuanweize/uni-ocr/pkgs/container/uni-ocr"><img src="https://img.shields.io/badge/GHCR-Docker-blue?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="README.md"><img src="https://img.shields.io/badge/Docs-English-blue?style=flat-square" alt="English Docs"></a>
</p>

---

**UniOCR** 是一个统一的多语言 OCR 抽象层，将最优秀的 OCR 引擎封装在一套简洁的接口之后。无论传入图片还是 PDF，都会返回结构化的文本、Markdown 和版面块信息 —— 无需关心底层使用了哪个引擎。

专为开发者、AI Agent 和自动化管线（n8n、Dify、Telegram Bot 等）设计。

## ✨ 核心特性

<div align="center">
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/dashboard.png" alt="UniOCR Web Dashboard" width="80%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  <br/><br/>
  <img src="https://raw.githubusercontent.com/yuanweize/uni-ocr/refs/heads/master/assets/settings.png" alt="UniOCR Hardware Radar" width="80%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
</div>

- 🖥️ **极其优雅的企业级控制台** — 全新构建的 Glassmorphism (毛玻璃) 现代化 Web UI，集成了交互式 OCR 游乐场、API 生成器及完整运行监控。
- 📊 **极客级硬件雷达** — 实时探测并轮询服务器物理底层状态：从 CPU/GPU 频率、内存/Swap 分配，到 Apple Neural Engine 及底层模型库真实加载状态，尽收眼底。
- 🔐 **军工级数据安全** — 内置本地 SQLite 持久化数据库。全面支持 2FA 动态令牌两步验证、Admin 强密码管理及私有/公开控制台一键切换。
- 🔑 **丝滑的 API Key 管理** — 界面化一键签发/吊销 API Token，并在生成时贴心提供组装好的专属 `curl` 联调代码片段。
- 🔌 **双擎无缝切换** — 深度文档 AI (PaddleOCR-VL) 与 macOS 原生视觉 (Apple Vision)，支持自动降级兜底。
- ⚡ **零配置满血加速** — 自动探测 Apple Silicon → 启动 MLX-VLM 引擎 → 满血调用 NPU 神经网络引擎。
- 🚀 **零时差智能缓存 (LRU)** — 对近期文件瞬间完成结果格式切换（TXT、JSON、MD、PDF），秒级下载与预览，拒绝重复消耗算力。
- 🐳 **Docker 极简部署** — 提供官方镜像，一行代码拉起完整的前后端生产级服务。

## 🚀 快速开始

### 方式一：pip 安装

```bash
# 核心包（轻量）
pip install uniocr

# 包含 PaddleOCR-VL（约 1.8 GB 模型，首次运行时下载）
pip install "uniocr[paddle]"

# 包含 Apple Vision（仅 macOS，零依赖）
pip install "uniocr[apple]"

# 全部安装 (推荐)
pip install "uniocr[all]"
```

### 方式二：Docker（推荐用于服务器）

```bash
# 或使用 Docker Compose（极速拉起所有组件）
curl -O https://raw.githubusercontent.com/yuanweize/uni-ocr/master/docker-compose.yml
docker compose up -d

# 检查运行状态
curl http://localhost:8000/health
```

## 📖 使用方式

### Python SDK

```python
from uniocr import UniOCR

ocr = UniOCR(engine="auto")          # 自动选择最佳引擎
doc = ocr.extract("发票.pdf")

print(doc.text)                       # 纯文本
print(doc.markdown)                   # 结构化 Markdown
print(doc.to_dict())                  # JSON 可序列化字典
```

### 命令行

```bash
# 启动完整的前后端 Web UI 服务控制台
uniocr serve --port 8000

# 提取文本（默认输出 Markdown）
uniocr extract document.pdf -o result.md

# 生成双层可搜索 PDF
uniocr extract input_image.jpg -o output_searchable.pdf
```

### REST API 与 控制台

```bash
# 启动
uniocr serve --port 8000
```
- **Web UI 控制台**: `http://localhost:8000/`
- **系统设置与硬件雷达**: `http://localhost:8000/settings`
- **交互式 API 文档**: `http://localhost:8000/docs`

#### API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查（含引擎列表） |
| `GET` | `/engines` | 列出当前环境可用的 OCR 引擎 |
| `POST` | `/extract` | 上传文件提取（返回 JSON/Markdown） |
| `POST` | `/extract/url` | 通过 URL 提取 |
| `POST` | `/extract/base64` | 通过 Base64 编码内容提取（JSON） |
| `POST` | `/extract/batch` | 一次请求批量提取多个文件 |
| `POST` | `/extract/pdf` | 上传文件提取（直接返回双层 PDF 文件） |

*(以上接口若关闭了公开访问，则均可通过在 Header 传入 `Authorization: Bearer <API_KEY>` 进行调用)*

## 🐳 Docker 部署

```bash
git clone https://github.com/yuanweize/uni-ocr.git
cd uni-ocr
docker compose up -d --build
```

`docker-compose.yml` 默认仅将 API 绑定到 `127.0.0.1`（如需局域网/远程访问，可覆盖 `UNIOCR_BIND_HOST`，例如设置为 Tailscale IP）。SQLite 数据库（管理员凭据、API Key、JWT 密钥）保存在具名卷中，容器重启后依然保留。

> **首次启动提示**：镜像默认使用 `admin`/`admin` 且开启了公开访问。请在首次启动后立即登录 `/settings`，设置真实密码，并在不希望匿名调用时关闭公开访问。

### 可选构建变体

```bash
# GPU 构建 —— 需要主机安装匹配的 CUDA 驱动和 NVIDIA Container Toolkit。
# 请选择不高于 `nvidia-smi` 显示的 CUDA 版本的 cuXXX 标签。
docker build \
  --build-arg PADDLE_PACKAGE=paddlepaddle-gpu==3.3.0 \
  --build-arg PADDLE_INDEX_URL=https://www.paddlepaddle.org.cn/packages/stable/cu126/ \
  -t uniocr:gpu .

# 在构建时预下载约 1.8GB 的 PaddleOCR-VL 模型，而非等到首次请求时再下载 ——
# 适用于网络隔离的部署环境。
docker build --build-arg PREDOWNLOAD_MODELS=true -t uniocr:offline-ready .
```

> 构建 GPU 镜像本身并不会启用 GPU 推理 —— 需要在运行容器时设置环境变量
> `UNIOCR_DEVICE=gpu`（或保持默认值 `auto`：只要安装的 paddle 版本能检测到可用
> GPU 就会自动使用，在纯 CPU 构建下则不做任何改变）。

## 🔧 引擎优先级

| 优先级 | 引擎 | 适用场景 | 速度 |
|--------|------|---------|------|
| 1 | **PaddleOCR-VL** + MLX-VLM | 复杂版面、表格、公式，109 种语言 | ⚡⚡ |
| 2 | **PaddleOCR-VL** (CPU) | 同上，未安装 MLX-VLM 时 | ⚡ |
| 3 | **Apple Vision** | 简单文本，仅 macOS，极速 | ⚡⚡⚡ |

> 在 Apple Silicon 上，安装 `mlx-vlm` 后 UniOCR 会**自动启动** MLX-VLM 服务，满载 NPU。完全零配置。

## 📄 许可证

[MIT](LICENSE) © 2026 Weize Yuan
