from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.log import logger
from app.models.platform import ComfyUIService
from app.schemas.base import Fail, Success
from app.settings.config import settings

router = APIRouter(prefix="/comfy", tags=["内部回调"])

# 缓存节点回调的 image_count，供 history sync 创建条目时使用，避免重复计数
_callback_cache: dict[int, dict[str, Any]] = {}


def get_callback_cache(project_id: int) -> dict[str, Any] | None:
    """供 history sync 查询某项目最近一次回调数据。查询后清除。"""
    return _callback_cache.pop(project_id, None)


class ComfyCallbackIn(BaseModel):
    project_id: int = Field(..., description="项目ID")
    prompt_id: Optional[str] = Field(None, description="ComfyUI prompt_id")
    status: str = Field(..., description="状态(成功/失败等)")
    concurrent_id: Optional[int] = Field(None, description="并发ID")
    image_count: int = Field(1, description="本次生成的图片数量")
    details: Optional[Any] = Field(None, description="详情(错误/耗时等)")
    timestamp: Optional[datetime] = Field(None, description="生成时间(可选，默认当前时间)")


@router.post("/callback", summary="ComfyUI 生成回调（secret 校验）")
async def comfy_callback(req_in: ComfyCallbackIn, x_platform_secret: str | None = Header(default=None)):
    secret = settings.PLATFORM_INTERNAL_SECRET
    if not secret:
        return Fail(code=500, msg="PLATFORM_INTERNAL_SECRET 未配置，回调已禁用")
    if not x_platform_secret or x_platform_secret != secret:
        return Fail(code=403, msg="invalid secret")

    svc = await ComfyUIService.filter(project_id=req_in.project_id).first()
    if not svc:
        return Fail(code=404, msg="service not found")

    _callback_cache[req_in.project_id] = {
        "image_count": req_in.image_count,
        "status": req_in.status,
        "details": req_in.details,
        "timestamp": req_in.timestamp or datetime.now(),
    }
    logger.info(
        f"[ComfyUI] callback cached: project={req_in.project_id} "
        f"image_count={req_in.image_count} status={req_in.status}"
    )

    return Success(
        data={
            "project_id": req_in.project_id,
            "user_id": svc.user_id,
            "image_count": req_in.image_count,
            "status": req_in.status,
            "cached": True,
        }
    )
