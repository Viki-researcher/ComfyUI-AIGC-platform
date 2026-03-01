from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from tortoise.functions import Sum

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
    total_users = await User.all().count()

    agg_all = await GenerationLog.all().annotate(total=Sum("image_count")).values("total")
    total_logs = agg_all[0]["total"] or 0 if agg_all else 0

    agg_today = await GenerationLog.filter(timestamp__gte=today_start).annotate(total=Sum("image_count")).values("total")
    today_logs = agg_today[0]["total"] or 0 if agg_today else 0

    agg_success = await GenerationLog.filter(status="成功").annotate(total=Sum("image_count")).values("total")
    success_logs = agg_success[0]["total"] or 0 if agg_success else 0

    online_comfy = await ComfyUIService.filter(status="online").count()
    online_annotation = await AnnotationService.filter(status="online").count()

    yesterday_start = today_start - timedelta(days=1)
    agg_yesterday = await GenerationLog.filter(
        timestamp__gte=yesterday_start, timestamp__lt=today_start
    ).annotate(total=Sum("image_count")).values("total")
    yesterday_logs = agg_yesterday[0]["total"] or 0 if agg_yesterday else 0

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
