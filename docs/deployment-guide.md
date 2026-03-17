# 菲特数据生成平台 — 部署指南

## 目录

- [快速开始](#快速开始)
- [Docker Compose 部署（推荐）](#docker-compose-部署推荐)
- [手动部署](#手动部署)
- [环境变量参考](#环境变量参考)
- [常见问题](#常见问题)

---

## 快速开始

### 环境要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Node.js | 20.19+ | 前端构建 |
| pnpm | 8.8+ | 前端包管理 |
| Python | 3.11+ | 后端运行 |
| PostgreSQL | 14+ | 生产数据库（开发可用 SQLite） |
| Docker + Compose | 24+ / 2.20+ | Docker 部署方式 |

### 30 秒快速体验（SQLite 开发模式）

```bash
# 1. 后端
cd vue-fastapi-admin-main
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DB_DEFAULT_CONNECTION=sqlite python run.py &

# 2. 前端
cd art-design-pro
pnpm install
pnpm dev --port 3006 --open false &

# 3. 访问 http://localhost:3006
# 默认账号: admin / 123456
```

---

## Docker Compose 部署（推荐）

### 1. 准备配置

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

```env
# LLM 配置（必填，否则 AI 对话不可用）
LLM_PROVIDER=openai             # openai / tongyi / ollama / custom
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini          # 对应提供商的模型名称

# 可选配置
LLM_API_BASE_URL=              # 留空使用默认地址
LLM_SYSTEM_PROMPT=你是菲特数据生成平台的AI助手
```

### 2. 启动所有服务

```bash
docker compose up -d
```

### 3. 访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3006 | 主界面 |
| 后端 API | http://localhost:8989 | REST API |
| API 文档 | http://localhost:8989/docs | Swagger UI |
| PostgreSQL | localhost:5432 | 数据库 |

默认账号：`admin` / `123456`

### 4. 查看日志

```bash
docker compose logs -f backend   # 后端日志
docker compose logs -f frontend  # 前端日志
docker compose logs -f postgres  # 数据库日志
```

### 5. 停止 / 重启

```bash
docker compose down              # 停止所有服务
docker compose restart backend   # 重启后端
docker compose up -d --build     # 重建并启动
```

### 6. 数据持久化

| 数据 | Docker Volume | 说明 |
|------|--------------|------|
| 数据库 | `pgdata` | PostgreSQL 数据文件 |
| 运行时 | `backend_runtime` | 上传文件、报表、日志 |

### 服务架构图

```
                    ┌──────────┐
    :3006 ──────────│ Nginx    │
                    │(frontend)│
                    └────┬─────┘
                         │ /api/* proxy
                    ┌────┴─────┐
    :8989 ──────────│ FastAPI  │
                    │(backend) │
                    └────┬─────┘
                         │
                    ┌────┴─────┐
    :5432 ──────────│PostgreSQL│
                    └──────────┘
```

---

## 手动部署

本节按**合理顺序**完成前后端、ComfyUI、数据生成、数据标注、PostgreSQL 等全部环境的安装与配置。所有 Python 环境均使用 `python3 -m venv .venv`，不采用 conda。

### 1. 前置条件与版本要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| OS | Ubuntu 20.04+ | 本文按 apt 编写 |
| Node.js | 20.19+ | 前端构建 |
| pnpm | 8.8+ | 前端包管理 |
| Python | 3.11+ | 后端、ComfyUI、标注工具 |
| PostgreSQL | 14+ | 生产数据库（开发可用 SQLite） |

### 2. 系统依赖

```bash
sudo apt update
sudo apt install -y git curl wget build-essential pkg-config \
  libpq-dev python3-dev python3-venv
```

- `libpq-dev`：后端连接 PostgreSQL 所需
- `python3-venv`：创建 Python 虚拟环境

### 3. Node.js 与 pnpm

```bash
# 使用 nvm 安装 Node.js（若已安装可跳过）
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
node -v   # 应 >= 20.19

# 安装 pnpm
npm i -g pnpm
pnpm -v
```

### 4. PostgreSQL 安装与初始化

#### 4.1 安装 PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 4.2 初始化数据库（策略 A：使用 postgres 用户，适合开发）

```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE data_generation OWNER postgres;"
```

或使用自动脚本：

```bash
cd docs/scripts
chmod +x install_postgres.sh
./install_postgres.sh
```

详细说明见 `docs/02_PostgreSQL_安装与初始化规范.md`。

### 5. 平台配置（单一事实源）

在项目根目录下，复制并编辑平台配置：

```bash
cd docs
cp .env.platform.example .env.platform
```

编辑 `.env.platform`，至少确认：

- `BACKEND_PORT`、`FRONTEND_PORT`：若端口被占用可修改
- `POSTGRES_PASSWORD`：与 4.2 中设置的密码一致
- `LLM_API_KEY`、`LLM_PROVIDER`、`LLM_MODEL`：AI 对话所需（可选，不填则 AI 对话不可用）

路径变量（`COMFULUI_ROOT`、`COMFYUI_REPO_PATH`、`ANNOTATION_TOOL_PATH` 等）默认使用相对路径，一般无需修改。

### 6. 后端环境（数据生成平台 API）

```bash
cd vue-fastapi-admin-main

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（二选一）：
# 方式 A：手动 export（适用于临时测试）
export DB_DEFAULT_CONNECTION=postgres
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=data_generation
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-your-key
export LLM_MODEL=gpt-4o-mini
export COMFYUI_REPO_PATH="$(pwd)/../ComfyUI-master-fitow"
export COMFYUI_PYTHON="$(pwd)/../ComfyUI-master-fitow/.venv/bin/python3"
export ANNOTATION_TOOL_PATH="$(pwd)/../sam3-annotation-tool"
export ANNOTATION_PYTHON="$(pwd)/../sam3-annotation-tool/.venv/bin/python3"

# 方式 B：创建 .env 文件（推荐，无需每次 export）
# 复制 docs/.env.platform 中的变量到 vue-fastapi-admin-main/.env，
# 或将下方内容写入 vue-fastapi-admin-main/.env（路径按实际调整）：
#   DB_DEFAULT_CONNECTION=postgres
#   POSTGRES_HOST=127.0.0.1
#   POSTGRES_PORT=5432
#   POSTGRES_USER=postgres
#   POSTGRES_PASSWORD=postgres
#   POSTGRES_DB=data_generation
#   COMFYUI_REPO_PATH=/path/to/ComfyUI-master-fitow
#   COMFYUI_PYTHON=/path/to/ComfyUI-master-fitow/.venv/bin/python3
#   ANNOTATION_TOOL_PATH=/path/to/sam3-annotation-tool
#   ANNOTATION_PYTHON=/path/to/sam3-annotation-tool/.venv/bin/
若使用方式 B，路径建议使用绝对路径，或相对于 vue-fastapi-admin-main 的路径（如 ../ComfyUI-master-fitow）
python3
# 后端会自动加载同目录下的 .env（该文件不在仓库中，需自行创建）

# 启动（开发模式）
python run.py

# 或生产模式
python -m uvicorn app:app --host 0.0.0.0 --port 8989 --workers 4
```

后端会在启动时自动执行数据库迁移并初始化默认数据（admin/123456）。

### 7. 前端环境

```bash
cd art-design-pro
pnpm install
```

**开发模式：**

```bash
# 确保 VITE_API_PROXY_URL 指向后端（见 art-design-pro/.env.development）
pnpm dev --host 0.0.0.0 --port 3006
```

**生产构建：**

```bash
pnpm build
# 产出目录: dist/，使用 Nginx 托管
```

端口与代理地址可通过 `docs/scripts/sync_ports_to_frontend.sh` 从 `.env.platform` 同步到前端 `.env.development`。

### 8. ComfyUI 环境（数据生成引擎）

```bash
cd ComfyUI-master-fitow

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖（含 PyTorch，耗时较长）
pip install -r requirements.txt

# 验证
python -c "import torch; print(torch.__version__)"
```

> 若工作流使用 **Google-Gemini**（Imagen）等 custom_nodes，需确保其依赖已安装。`requirements.txt` 已包含 `google-genai`；若使用其他节点，请在 ComfyUI 的 Manager 中安装或手动 `pip install` 对应依赖。

在 `.env.platform` 中设置：

```bash
COMFYUI_PYTHON="${COMFULUI_ROOT}/ComfyUI-master-fitow/.venv/bin/python3"
```

若为 CPU 模式，设置 `COMFYUI_FORCE_CPU=true`。

### 9. 数据标注环境（SAM3 Annotation Tool）

```bash
cd sam3-annotation-tool

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 升级 pip（推荐，避免 PEP 517 构建问题）
pip install --upgrade pip

# 安装依赖（pyproject.toml，含 transformers、gradio、torch 等）
# 根据硬件选择其一：

# 有 NVIDIA GPU（按 CUDA 版本选择，如 12.6）：
pip install -e . --extra-index-url https://download.pytorch.org/whl/cu126

# 无 GPU 或仅 CPU：
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# 其他 CUDA 版本：cu121、cu124 等，见 https://pytorch.org/get-started/locally/
```

以上方式可能导致transformer库安装失败，可按以下方式单独安装

```python
# 1.下载transformer库
# https://github.com/huggingface/transformers/tree/7be2d3587efede549bfde514ffb7a00e6a9baa20

# 2.
unzip transformers-7be2d3587efede549bfde514ffb7a00e6a9baa20.zip && mv transformers-7be2d3587efede549bfde514ffb7a00e6a9baa20.zip transformers
cd transformers
pip install .

# 3.屏蔽requirements.txt，执行以下命令进行安装
pip install -r requirements.txt
```

在 `.env.platform` 中设置：

```bash
ANNOTATION_TOOL_PATH="${COMFULUI_ROOT}/sam3-annotation-tool"
ANNOTATION_PYTHON="${COMFULUI_ROOT}/sam3-annotation-tool/.venv/bin/python3"
```

> 说明：SAM3 为 HuggingFace gated model，需设置 `HF_TOKEN` 并申请 `facebook/sam3` 访问权限才能使用推理功能。未配置时 Gradio UI 仍可正常启动。

### 10. 启动与验证

**方式一：手动分别启动**

```bash
# 终端 1：后端
cd vue-fastapi-admin-main && source .venv/bin/activate
# 加载 .env.platform 或 export 环境变量后：
python run.py

# 终端 2：前端
cd art-design-pro
pnpm dev --host 0.0.0.0 --port 3006
```

ComfyUI 与数据标注由后端在用户操作时按需拉起，无需单独启动。

**方式二：一键脚本（推荐）**

```bash
cd docs
chmod +x scripts/*.sh
./scripts/start_all.sh    # 启动前后端
./scripts/status.sh       # 查看状态
./scripts/stop_all.sh     # 停止
```

访问 `http://localhost:3006`，默认账号：`admin` / `123456`。

### 11. Nginx 配置示例（生产部署）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/art-design-pro/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8989;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

---

## 环境变量参考

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_DEFAULT_CONNECTION` | `postgres` | 数据库类型: `postgres` 或 `sqlite` |
| `POSTGRES_HOST` | `127.0.0.1` | PostgreSQL 地址 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_USER` | `postgres` | PostgreSQL 用户 |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL 密码 |
| `POSTGRES_DB` | `data_generation` | 数据库名 |

### LLM 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` | 提供商: openai/tongyi/ollama/custom 等 |
| `LLM_API_KEY` | - | API 密钥 |
| `LLM_API_BASE_URL` | 自动 | API 基地址 |
| `LLM_MODEL` | `gpt-4o-mini` | 默认模型 |
| `LLM_MAX_TOKENS` | `4096` | 最大 Token |
| `LLM_TEMPERATURE` | `0.7` | 生成温度 |
| `LLM_SYSTEM_PROMPT` | 内置 | 系统提示词 |
| `LLM_PROVIDERS_JSON` | `[]` | 多提供商配置(JSON) |

### RAG 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_ENABLED` | `true` | 启用 RAG |
| `RAG_CHUNK_SIZE` | `500` | 分块大小 |
| `RAG_CHUNK_OVERLAP` | `50` | 重叠字符数 |
| `RAG_TOP_K` | `3` | 检索数量 |
| `RAG_UPLOAD_DIR` | `runtime/chat_uploads` | 上传目录 |

### Embedding 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_API_KEY` | 复用 LLM | 嵌入 API 密钥 |
| `EMBEDDING_API_BASE_URL` | 复用 LLM | 嵌入 API 基地址 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 嵌入模型 |

### 局域网访问

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PLATFORM_PUBLIC_HOST` | 自动 | 平台对外 IP，ComfyUI/标注跳转 URL 使用；留空时 start_all 自动取本机主 IP |
| `COMFYUI_LISTEN` | `0.0.0.0` | 监听地址，局域网访问需 `0.0.0.0` |

### ComfyUI 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COMFYUI_REPO_PATH` | - | ComfyUI 仓库路径 |
| `COMFYUI_PYTHON` | - | ComfyUI venv 的 python 路径 |
| `COMFYUI_LISTEN` | `0.0.0.0` | 监听地址（局域网需 0.0.0.0） |
| `COMFYUI_PORT_RANGE` | `8200-8299` | 端口范围 |
| `COMFYUI_FORCE_CPU` | `false` | 强制 CPU 模式 |

### 数据标注配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANNOTATION_TOOL_PATH` | - | 标注工具目录 |
| `ANNOTATION_PYTHON` | - | 标注工具 venv 的 python 路径，为空时回退 uv/python3 |
| `ANNOTATION_LISTEN` | `127.0.0.1` | Gradio 监听地址 |
| `ANNOTATION_PORT_RANGE` | `7860-7899` | 端口池 |

---

## 常见问题

### Q: 后端启动报 `COMFYUI_REPO_PATH is empty` 警告

这是正常的。如果不需要 ComfyUI 数据生成功能（只用 AI 对话），可以忽略这个警告。

### Q: AI 对话返回 401 错误

检查 `LLM_API_KEY` 是否正确配置。不同提供商的 Key 格式不同：
- OpenAI: `sk-proj-xxx...`
- 其他提供商: `sk-xxx...`

### Q: Docker 构建前端失败

确保 `pnpm-lock.yaml` 文件存在且与 `package.json` 匹配。如果缺失，先在本地运行 `pnpm install` 生成。

### Q: SSE 流式响应不工作

检查 Nginx 配置是否关闭了 `proxy_buffering`:
```nginx
proxy_buffering off;
```

### Q: LLM API Key 被 CI/CD 占位符覆盖

自 v0.3+ 起，后端内置 API Key 回退机制。`Settings.model_post_init` 在启动时检测无效的 Key（长度 < 8、纯数字、`"123"`、`"test"` 等占位值），自动回退到 `.env` 文件中配置的值。无需手动处理 Cloud Agent 或 CI/CD 注入的占位符环境变量。

### Q: 数据生成失败：`No module named 'google'`

工作流使用 **Google-Gemini**（Imagen）节点时，需安装 `google-genai`。ComfyUI 的 `requirements.txt` 已包含该依赖；若之前未安装，执行：

```bash
cd ComfyUI-master-fitow
source .venv/bin/activate
pip install "google-genai>=1.51.0"
```

然后重启 ComfyUI 实例（关闭数据生成页面后重新打开，或执行 `docs/scripts/stop_all.sh` 再 `start_all.sh`）。

### Q: 数据标注安装失败：`Failed to build transformers` / `unable to access github.com`

sam3-annotation-tool 依赖从 GitHub 克隆 `transformers`。若网络无法访问 GitHub（超时、防火墙等），可尝试：

1. **配置代理**（若有）：`export https_proxy=http://...`
2. **使用镜像**：配置 git 使用 GitHub 镜像后重试
3. **暂不安装**：数据标注为可选功能，可先使用平台其他功能；待网络畅通后再执行 `pip install -e .`

### Q: 数据库迁移

后端启动时自动运行 Aerich 迁移。如果需要手动操作：
```bash
cd vue-fastapi-admin-main
source .venv/bin/activate
aerich migrate     # 生成迁移文件
aerich upgrade     # 应用迁移
```

---

*文档版本：v0.4.0*  
*更新日期：2026-03-08*
