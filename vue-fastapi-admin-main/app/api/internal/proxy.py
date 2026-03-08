"""
后端代理：中转 ComfyUI 自定义节点的外部 API 调用（如 147ai.com），
实现对 API 使用的记录、统计与管控。

节点侧只需将 base_url 从 https://147ai.com 改为 http://127.0.0.1:9999/api/internal/proxy/147ai，
后端负责：
  1. 鉴权（PLATFORM_INTERNAL_SECRET）
  2. 转发请求至真实 API
  3. 记录调用日志
"""

from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Header, Request
from fastapi.responses import Response

from app.log import logger
from app.models.platform import ComfyUIService
from app.schemas.base import Fail
from app.settings.config import settings

router = APIRouter(prefix="/proxy", tags=["内部代理"])

REAL_147AI_URL = "https://147ai.com"


@router.api_route(
    "/147ai/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    summary="代理 147ai.com API 并记录用量",
)
async def proxy_147ai(
    path: str,
    request: Request,
    x_platform_secret: str | None = Header(default=None),
    x_platform_project_id: str | None = Header(default=None),
):
    secret = settings.PLATFORM_INTERNAL_SECRET
    if secret and (not x_platform_secret or x_platform_secret != secret):
        return Fail(code=403, msg="invalid secret")

    body = await request.body()
    headers = {}
    for key, val in request.headers.items():
        low = key.lower()
        if low in ("host", "content-length", "transfer-encoding"):
            continue
        if low.startswith("x-platform-"):
            continue
        headers[key] = val

    target_url = f"{REAL_147AI_URL}/{path}"
    t0 = time.time()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

        elapsed = round(time.time() - t0, 2)

        project_id = int(x_platform_project_id) if x_platform_project_id else None
        if project_id:
            try:
                await _record_proxy_usage(project_id, path, elapsed, resp.status_code)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Proxy] record usage failed: {e}")

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )

    except Exception as e:
        logger.error(f"[Proxy] 147ai proxy error: {e}")
        return Fail(code=502, msg=f"Proxy error: {e}")


async def _record_proxy_usage(project_id: int, path: str, elapsed: float, status_code: int) -> None:
    svc = await ComfyUIService.filter(project_id=project_id).first()
    if not svc:
        return

    logger.info(f"[Proxy] recorded: project={project_id} path={path} elapsed={elapsed}s status={status_code}")
