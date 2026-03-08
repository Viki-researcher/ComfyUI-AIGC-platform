from fastapi import APIRouter

from .comfy import router as comfy_router
from .proxy import router as proxy_router

internal_router = APIRouter(prefix="/internal")
internal_router.include_router(comfy_router)
internal_router.include_router(proxy_router)

__all__ = ["internal_router"]

