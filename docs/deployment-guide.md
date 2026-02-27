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
| 后端 API | http://localhost:9999 | REST API |
| API 文档 | http://localhost:9999/docs | Swagger UI |
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
    :9999 ──────────│ FastAPI  │
                    │(backend) │
                    └────┬─────┘
                         │
                    ┌────┴─────┐
    :5432 ──────────│PostgreSQL│
                    └──────────┘
```

---

## 手动部署

### 后端部署

```bash
cd vue-fastapi-admin-main

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DB_DEFAULT_CONNECTION=postgres
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=data_generation
export LLM_PROVIDER=openai      # 或其他提供商
export LLM_API_KEY=sk-your-key
export LLM_MODEL=gpt-4o-mini   # 对应模型名称

# 启动（开发模式，带热重载）
python run.py

# 启动（生产模式）
python -m uvicorn app:app --host 0.0.0.0 --port 9999 --workers 4
```

### 前端部署

#### 开发模式

```bash
cd art-design-pro
pnpm install
pnpm dev --host 0.0.0.0 --port 3006
```

#### 生产构建

```bash
cd art-design-pro
pnpm install
pnpm build

# 产出目录: dist/
# 使用 Nginx 托管 dist/ 目录
```

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/art-design-pro/dist;
    index index.html;

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;          # SSE 流式响应必须关闭缓冲
        proxy_read_timeout 300s;      # LLM 响应可能较慢
    }
}
```

### 一键脚本部署（适用于开发联调）

```bash
cd docs
cp .env.platform.example .env.platform
# 编辑 .env.platform 修改路径和端口
chmod +x scripts/*.sh
./scripts/start_all.sh    # 启动
./scripts/status.sh       # 状态
./scripts/stop_all.sh     # 停止
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

### ComfyUI 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COMFYUI_REPO_PATH` | - | ComfyUI 仓库路径 |
| `COMFYUI_PYTHON` | - | ComfyUI Python 路径 |
| `COMFYUI_LISTEN` | `127.0.0.1` | 监听地址 |
| `COMFYUI_PORT_RANGE` | `8200-8299` | 端口范围 |
| `COMFYUI_FORCE_CPU` | `false` | 强制 CPU 模式 |

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

### Q: 数据库迁移

后端启动时自动运行 Aerich 迁移。如果需要手动操作：
```bash
cd vue-fastapi-admin-main
source .venv/bin/activate
aerich migrate     # 生成迁移文件
aerich upgrade     # 应用迁移
```
