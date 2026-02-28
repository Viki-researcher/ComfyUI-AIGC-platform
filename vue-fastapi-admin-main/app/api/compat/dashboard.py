from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter

from app.core.dependency import DependPermission
from app.models.admin import User
from app.models.platform import ComfyUIService, AnnotationService, GenerationLog, Project
from app.schemas.base import Success

router = APIRouter(prefix="/dashboard", tags=["仪表盘模块"])


@router.get("", summary="仪表盘概览", dependencies=[DependPermission])
async def get_dashboard():
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_projects = await Project.all().count()
    total_logs = await GenerationLog.all().count()
    today_logs = await GenerationLog.filter(timestamp__gte=today_start).count()
    success_logs = await GenerationLog.filter(status="成功").count()
    total_users = await User.all().count()

    online_comfy = await ComfyUIService.filter(status="online").count()
    online_annotation = await AnnotationService.filter(status="online").count()

    yesterday_start = today_start - timedelta(days=1)
    yesterday_logs = await GenerationLog.filter(
        timestamp__gte=yesterday_start, timestamp__lt=today_start
    ).count()

    return Success(data={
        "today_count": today_logs,
        "yesterday_count": yesterday_logs,
        "total_count": total_logs,
        "success_count": success_logs,
        "success_rate": round(success_logs / total_logs * 100, 1) if total_logs > 0 else 0,
        "active_projects": total_projects,
        "total_users": total_users,
        "online_comfy": online_comfy,
        "online_annotation": online_annotation,
    })
