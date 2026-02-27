"""
Agent 工具框架 — Function Calling 工具注册与执行

提供 ToolRegistry 管理工具定义，内置以下工具：
- list_projects: 查询项目列表
- query_generation_logs: 查询生成日志（含筛选与统计）
- get_server_stats: 获取服务器 CPU/内存/磁盘状态
- analyze_anomalies: 检测近期失败率异常
- export_report_excel: 导出生成日志为 Excel 报表
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine

import psutil
from openpyxl import Workbook
from tortoise.expressions import Q

from app.log import logger
from app.models.platform import GenerationLog, Project
from app.settings.config import settings


# ---------------------------------------------------------------------------
# ToolRegistry — 工具注册中心
# ---------------------------------------------------------------------------

class ToolRegistry:
    """管理可用的 Agent 工具定义与实现。"""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[..., Coroutine]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Coroutine],
    ) -> None:
        """注册一个工具。"""
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler

    def get_definitions(self) -> list[dict[str, Any]]:
        """返回 OpenAI Function Calling 格式的工具定义列表。"""
        return list(self._tools.values())

    async def call(self, name: str, arguments: dict[str, Any], user_id: int) -> str:
        """执行指定工具并返回字符串结果。"""
        handler = self._handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
        try:
            return await handler(user_id=user_id, **arguments)
        except Exception as exc:
            logger.error(f"[AgentTool] 工具 {name} 执行异常: {exc}")
            return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 全局注册表实例
# ---------------------------------------------------------------------------
_registry = ToolRegistry()


# ---------------------------------------------------------------------------
# 内置工具实现
# ---------------------------------------------------------------------------

async def _list_projects(user_id: int, **_kwargs: Any) -> str:
    """查询项目列表。"""
    projects = await Project.all().order_by("-created_at").limit(50)
    data = []
    for p in projects:
        data.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "note": p.note or "",
            "owner_user_id": p.owner_user_id,
            "created_at": p.created_at.strftime(settings.DATETIME_FORMAT) if p.created_at else "",
        })
    return json.dumps({"projects": data, "total": len(data)}, ensure_ascii=False)


async def _query_generation_logs(
    user_id: int,
    project_id: int | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **_kwargs: Any,
) -> str:
    """查询生成日志，支持按项目、状态、日期范围筛选，并返回汇总统计。"""
    q = Q()
    if project_id is not None:
        q &= Q(project_id=project_id)
    if status:
        q &= Q(status=status)
    if start_date:
        q &= Q(timestamp__gte=datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        q &= Q(timestamp__lte=datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))

    rows = await GenerationLog.filter(q).order_by("-timestamp").limit(500)
    total = len(rows)
    success_count = sum(1 for r in rows if r.status == "成功")
    fail_count = sum(1 for r in rows if r.status == "失败")

    summary = {
        "total": total,
        "success": success_count,
        "fail": fail_count,
        "success_rate": round(success_count / total * 100, 2) if total else 0,
        "recent_logs": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "user_id": r.user_id,
                "status": r.status,
                "timestamp": r.timestamp.strftime(settings.DATETIME_FORMAT) if r.timestamp else "",
            }
            for r in rows[:20]
        ],
    }
    return json.dumps(summary, ensure_ascii=False)


async def _get_server_stats(user_id: int, **_kwargs: Any) -> str:
    """获取服务器 CPU / 内存 / 磁盘状态。"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    data = {
        "cpu_percent": cpu_percent,
        "cpu_count": psutil.cpu_count(),
        "memory": {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "percent": disk.percent,
        },
    }
    return json.dumps(data, ensure_ascii=False)


async def _analyze_anomalies(user_id: int, **_kwargs: Any) -> str:
    """
    检测近期生成日志失败率异常。
    对比最近 7 天与前 7 天的失败率，判断是否存在异常上升。
    """
    now = datetime.now()
    recent_start = now - timedelta(days=7)
    baseline_start = now - timedelta(days=14)

    recent_rows = await GenerationLog.filter(timestamp__gte=recent_start).all()
    baseline_rows = await GenerationLog.filter(
        timestamp__gte=baseline_start,
        timestamp__lt=recent_start,
    ).all()

    recent_total = len(recent_rows)
    recent_fail = sum(1 for r in recent_rows if r.status == "失败")
    baseline_total = len(baseline_rows)
    baseline_fail = sum(1 for r in baseline_rows if r.status == "失败")

    recent_rate = round(recent_fail / recent_total * 100, 2) if recent_total else 0
    baseline_rate = round(baseline_fail / baseline_total * 100, 2) if baseline_total else 0

    anomaly = False
    message = "近 7 天失败率正常"
    if recent_total > 0 and recent_rate > baseline_rate + 10:
        anomaly = True
        message = f"近 7 天失败率 ({recent_rate}%) 显著高于基线 ({baseline_rate}%)，请关注"

    result = {
        "anomaly_detected": anomaly,
        "message": message,
        "recent_7d": {"total": recent_total, "fail": recent_fail, "fail_rate": recent_rate},
        "baseline_7d": {"total": baseline_total, "fail": baseline_fail, "fail_rate": baseline_rate},
    }
    return json.dumps(result, ensure_ascii=False)


async def _export_report_excel(
    user_id: int,
    project_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **_kwargs: Any,
) -> str:
    """导出生成日志为 Excel 报表，返回文件路径。"""
    q = Q()
    if project_id is not None:
        q &= Q(project_id=project_id)
    if start_date:
        q &= Q(timestamp__gte=datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        q &= Q(timestamp__lte=datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))

    rows = await GenerationLog.filter(q).order_by("-timestamp").limit(5000)

    wb = Workbook()
    ws = wb.active
    ws.title = "生成日志"
    ws.append(["ID", "项目ID", "用户ID", "状态", "Prompt ID", "时间"])

    for r in rows:
        ws.append([
            r.id,
            r.project_id,
            r.user_id,
            r.status,
            r.prompt_id or "",
            r.timestamp.strftime(settings.DATETIME_FORMAT) if r.timestamp else "",
        ])

    reports_dir = os.path.join(settings.BASE_DIR, "runtime", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(reports_dir, filename)
    wb.save(filepath)

    logger.info(f"[AgentTool] 导出报表: {filepath} ({len(rows)} 条)")
    return json.dumps({
        "file_path": filepath,
        "file_name": filename,
        "row_count": len(rows),
        "download_url": f"/api/reports/{filename}",
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 注册内置工具
# ---------------------------------------------------------------------------

_registry.register(
    name="list_projects",
    description="查询项目列表，返回所有项目的名称、编号、创建时间等信息",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
    handler=_list_projects,
)

_registry.register(
    name="query_generation_logs",
    description="查询数据生成日志，支持按项目ID、状态、日期范围筛选，返回汇总统计和最近记录",
    parameters={
        "type": "object",
        "properties": {
            "project_id": {"type": "integer", "description": "项目ID（可选）"},
            "status": {"type": "string", "description": "状态筛选，如 '成功' 或 '失败'（可选）"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD（可选）"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD（可选）"},
        },
        "required": [],
    },
    handler=_query_generation_logs,
)

_registry.register(
    name="get_server_stats",
    description="获取服务器运行状态，包括 CPU 使用率、内存使用量、磁盘占用等信息",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
    handler=_get_server_stats,
)

_registry.register(
    name="analyze_anomalies",
    description="分析近期数据生成的异常情况，对比最近7天与前7天的失败率，检测是否有失败率飙升",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
    handler=_analyze_anomalies,
)

_registry.register(
    name="export_report_excel",
    description="将数据生成日志导出为 Excel 报表文件，支持按项目和日期范围筛选，返回文件下载路径",
    parameters={
        "type": "object",
        "properties": {
            "project_id": {"type": "integer", "description": "项目ID（可选）"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD（可选）"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD（可选）"},
        },
        "required": [],
    },
    handler=_export_report_excel,
)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def get_tool_definitions() -> list[dict[str, Any]]:
    """返回 OpenAI Function Calling 格式的全部工具定义。"""
    return _registry.get_definitions()


async def execute_tool(tool_name: str, arguments: dict[str, Any], user_id: int) -> str:
    """执行指定工具，返回字符串结果。"""
    logger.info(f"[AgentTool] 执行工具: {tool_name}, 参数: {arguments}, user_id={user_id}")
    return await _registry.call(tool_name, arguments, user_id)
