# Docker Compose 容器化部署指南

## 服务架构

```
┌─────────────┐    ┌─────────────┐
│   Frontend   │───▶│   Backend   │
│  (Vite:3006) │    │(FastAPI:9999)│
└─────────────┘    └──────┬──────┘
                          │
                   ┌──────┴──────┐
                   ▼             ▼
              ┌──────────┐ ┌──────────┐
              │PostgreSQL │ │  Redis   │
              │ (:5432)   │ │ (:6379)  │
              └──────────┘ └──────────┘
```

## 快速启动

```bash
# 克隆仓库后进入根目录
cd /path/to/ComfyUI-AIGC-platform

# 一键启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 停止所有服务
docker compose down

# 停止并清除数据
docker compose down -v
```

## 服务说明

| 服务 | 镜像 | 端口 | 健康检查 |
|------|------|------|----------|
| `db` | postgres:16-alpine | 5432 | `pg_isready` |
| `redis` | redis:7-alpine | 6379 | `redis-cli ping` |
| `backend` | 自定义构建 | 9999 | 依赖 db 就绪 |
| `frontend` | 自定义构建 | 3006 | 依赖 backend |

## 数据持久化

| Volume | 说明 |
|--------|------|
| `pgdata` | PostgreSQL 数据库文件 |
| `backend_runtime` | 后端运行时（ComfyUI 日志、实例等） |
| bind mount | ComfyUI 和标注工具目录（宿主机直接挂载） |

## 环境变量

所有环境变量在 `docker-compose.yml` 的 `environment` 段中配置。关键变量：

- `DB_DEFAULT_CONNECTION=postgres`
- `POSTGRES_HOST=db`（使用 Docker 服务名）
- `COMFYUI_REPO_PATH=/workspace/ComfyUI-master-fitow`
- `ANNOTATION_TOOL_PATH=/workspace/sam3-annotation-tool`

## 自定义配置

修改 `docker-compose.yml` 中的端口映射或环境变量后，重新启动即可：

```bash
docker compose up -d --build
```
