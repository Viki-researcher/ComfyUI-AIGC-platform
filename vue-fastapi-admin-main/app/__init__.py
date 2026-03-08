import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)
from app.log import logger
from app.services.comfyui_history_sync import sync_loop
from app.services.comfyui_manager import heartbeat_loop, stop_pid

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


async def _stop_all_child_services() -> None:
    """后端关闭时，停止所有通过平台启动的 ComfyUI 和标注服务进程。"""
    from app.models.platform import AnnotationService, ComfyUIService

    for svc in await ComfyUIService.filter(status="online").all():
        if svc.pid:
            try:
                stop_pid(int(svc.pid), timeout_seconds=5)
                logger.info(f"[Shutdown] stopped ComfyUI pid={svc.pid} (project={svc.project_id})")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Shutdown] failed to stop ComfyUI pid={svc.pid}: {e}")
        svc.status = "offline"
        await svc.save()

    for svc in await AnnotationService.filter(status="online").all():
        if svc.pid:
            try:
                stop_pid(int(svc.pid), timeout_seconds=5)
                logger.info(f"[Shutdown] stopped Annotation pid={svc.pid} (project={svc.project_id})")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Shutdown] failed to stop Annotation pid={svc.pid}: {e}")
        svc.status = "offline"
        await svc.save()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()
    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(heartbeat_loop(stop_event))
    sync_task = asyncio.create_task(sync_loop(stop_event, interval_seconds=int(settings.COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS)))
    yield
    # ---- shutdown ----
    stop_event.set()
    hb_task.cancel()
    sync_task.cancel()
    with suppress(Exception):
        await hb_task
    with suppress(Exception):
        await sync_task
    await _stop_all_child_services()
    await Tortoise.close_connections()
    logger.info("[Shutdown] backend shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")
    return app


app = create_app()
