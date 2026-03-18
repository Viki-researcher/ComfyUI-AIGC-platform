import os
import typing

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_dotenv_value(key: str, env_file: str = ".env") -> str | None:
    """直接从 .env 文件读取指定 key 的值（不受环境变量覆盖影响）。"""
    try:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    VERSION: str = "0.4.0"
    APP_TITLE: str = "Vue FastAPI Admin"
    PROJECT_NAME: str = "Vue FastAPI Admin"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]

    DEBUG: bool = True

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    # 数据库默认连接（需求：PostgreSQL 异步连接）。可通过环境变量切换：
    # - DB_DEFAULT_CONNECTION=postgres|sqlite
    DB_DEFAULT_CONNECTION: str = "postgres"

    # PostgreSQL（asyncpg）
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "data_generation"

    # ComfyUI 进程管理（数据生成平台）
    # - COMFYUI_REPO_PATH: ComfyUI 仓库根目录（例如 .../ComfyUI-master-fitow）
    # - COMFYUI_PYTHON: ComfyUI 环境的 python 可执行文件路径
    COMFYUI_REPO_PATH: str = ""
    COMFYUI_PYTHON: str = ""
    # ComfyUI 进程监听地址（传给 `python main.py --listen`）
    # - 仅本机访问：127.0.0.1
    # - 局域网/远程访问：0.0.0.0
    COMFYUI_LISTEN: str = "127.0.0.1"
    # 后端内部访问 ComfyUI 的主机名/IP（用于健康检查、history 拉取等）。
    # 默认自动推导：若 COMFYUI_LISTEN=0.0.0.0，则 internal_host=127.0.0.1；否则 internal_host=COMFYUI_LISTEN。
    COMFYUI_INTERNAL_HOST: str = ""
    # 前端打开 ComfyUI 的对外访问基地址（可选）。
    # 例如：COMFYUI_PUBLIC_BASE_URL="http://10.10.1.199"（无需带端口，端口由后端分配后拼接）
    # 为空时：后端会尝试从请求的 Host / X-Forwarded-* 推导；若仍为 localhost 则用 PLATFORM_PUBLIC_HOST。
    COMFYUI_PUBLIC_BASE_URL: str = ""
    # 平台对外 IP/host（局域网访问时必填）。当请求 Host 为 localhost 时，ComfyUI/标注跳转 URL 使用此值。
    PLATFORM_PUBLIC_HOST: str = ""
    COMFYUI_PORT_RANGE: str = "8200-8299"
    COMFYUI_INSTANCE_BASE_DIR: str = os.path.join("runtime", "comfy_instances")
    COMFYUI_LOG_DIR: str = os.path.join("runtime", "comfy_logs")
    COMFYUI_STARTUP_TIMEOUT_SECONDS: int = 60
    COMFYUI_HEARTBEAT_INTERVAL_SECONDS: int = 30
    COMFYUI_FORCE_CPU: bool = False
    COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS: int = 10

    # 统一输出目录：所有项目的生成图片集中存放（按 项目名/YYYYMMDD 组织）
    # 为空时使用 runtime/output
    OUTPUT_BASE_DIR: str = os.path.join("runtime", "output")

    # ComfyUI -> 平台回调（可选）
    PLATFORM_INTERNAL_SECRET: str = ""
    PLATFORM_CALLBACK_URL: str = "http://127.0.0.1:8989/api/internal/comfy/callback"

    # 数据标注（SAM3 Annotation Tool）
    ANNOTATION_TOOL_PATH: str = ""
    ANNOTATION_PYTHON: str = ""  # 标注工具 venv 的 python 路径，为空时回退到 uv/python3
    ANNOTATION_LISTEN: str = "127.0.0.1"
    ANNOTATION_INTERNAL_HOST: str = ""
    ANNOTATION_PUBLIC_BASE_URL: str = ""
    ANNOTATION_PORT_RANGE: str = "7860-7899"
    ANNOTATION_LOG_DIR: str = os.path.join("runtime", "annotation_logs")
    ANNOTATION_STARTUP_TIMEOUT_SECONDS: int = 300  # SAM3 模型加载较慢，默认 5 分钟
    # SAM3 模型本地路径（HuggingFace 格式目录）。留空则使用 facebook/sam3（Hub 或缓存）
    ANNOTATION_SAM3_MODEL_PATH: str = ""

    # ===== LLM / AI Chat 配置 =====
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_API_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_SYSTEM_PROMPT: str = "你是菲特数据生成平台的AI助手，请用中文回答用户问题。"
    LLM_PROVIDERS_JSON: str = "[]"

    # Embedding 配置 (RAG)
    EMBEDDING_PROVIDER: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE_URL: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # RAG 配置
    RAG_ENABLED: bool = True
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 3
    RAG_UPLOAD_DIR: str = os.path.join("runtime", "chat_uploads")

    TORTOISE_ORM: dict = {}
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        # 防止外部注入的无效 LLM_API_KEY 覆盖 .env 中的有效配置。
        # 当环境变量中的 key 明显无效（过短 / 纯数字 / 常见占位符）时，
        # 回退到 .env 文件中的值。
        _LLM_PLACEHOLDER_VALUES = {"", "123", "test", "key", "your-api-key", "sk-xxx", "xxx"}
        if self.LLM_API_KEY.strip() in _LLM_PLACEHOLDER_VALUES or (
            len(self.LLM_API_KEY.strip()) < 8 and not self.LLM_API_KEY.startswith("sk-")
        ):
            dotenv_key = _read_dotenv_value("LLM_API_KEY")
            if dotenv_key and len(dotenv_key) >= 8:
                self.LLM_API_KEY = dotenv_key

        if not self.LLM_API_BASE_URL:
            dotenv_base = _read_dotenv_value("LLM_API_BASE_URL")
            if dotenv_base:
                self.LLM_API_BASE_URL = dotenv_base

        if self.LLM_PROVIDER in ("openai",) and _read_dotenv_value("LLM_PROVIDER"):
            dotenv_provider = _read_dotenv_value("LLM_PROVIDER")
            if dotenv_provider and dotenv_provider != self.LLM_PROVIDER:
                self.LLM_PROVIDER = dotenv_provider

        if self.LLM_MODEL in ("gpt-4o-mini",) and _read_dotenv_value("LLM_MODEL"):
            dotenv_model = _read_dotenv_value("LLM_MODEL")
            if dotenv_model and dotenv_model != self.LLM_MODEL:
                self.LLM_MODEL = dotenv_model

        self.TORTOISE_ORM = {
            "connections": {
                "sqlite": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": f"{self.BASE_DIR}/db.sqlite3"},
                },
                "postgres": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": self.POSTGRES_HOST,
                        "port": self.POSTGRES_PORT,
                        "user": self.POSTGRES_USER,
                        "password": self.POSTGRES_PASSWORD,
                        "database": self.POSTGRES_DB,
                    },
                },
            },
            "apps": {
                "models": {
                    "models": ["app.models", "aerich.models"],
                    "default_connection": self.DB_DEFAULT_CONNECTION,
                },
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }


settings = Settings()
