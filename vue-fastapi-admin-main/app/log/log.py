import os
import sys

from loguru import logger as loguru_logger

from app.settings import settings


class Loggin:
    def __init__(self) -> None:
        debug = settings.DEBUG
        if debug:
            self.level = "DEBUG"
        else:
            self.level = "INFO"

    def setup_logger(self):
        loguru_logger.remove()
        loguru_logger.add(sink=sys.stdout, level=self.level)

        # 错误日志写入文件，便于后台运行时排查（如标注/ComfyUI 启动失败等）
        log_dir = os.path.join(settings.BASE_DIR, "runtime")
        os.makedirs(log_dir, exist_ok=True)
        error_log_path = os.path.join(log_dir, "backend_error.log")
        loguru_logger.add(
            sink=error_log_path,
            level="ERROR",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )
        return loguru_logger


loggin = Loggin()
logger = loggin.setup_logger()
