from __future__ import annotations

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.log import logger
from app.models.platform import ComfyUIService, GenerationLog, Project


async def _fetch_history(comfy_url: str, *, max_items: int = 50) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{comfy_url}/history", params={"max_items": max_items})
        r.raise_for_status()
        return r.json()


def _map_status(history_item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = history_item.get("status") or {}
    status_str = status.get("status_str") or ""
    if status_str == "success":
        return "成功", {"status": status}
    if status_str == "error":
        return "失败", {"status": status}
    return "未知", {"status": status}


def _count_output_images(history_item: dict[str, Any]) -> int:
    """从 ComfyUI history item 的 outputs 中统计生成的图片数量。"""
    outputs = history_item.get("outputs") or {}
    count = 0
    for _node_id, node_output in outputs.items():
        if isinstance(node_output, dict):
            images = node_output.get("images") or []
            count += len(images)
    return max(count, 1)


def _collect_output_files(history_item: dict[str, Any]) -> list[dict[str, str]]:
    """收集 history item 中的输出图片文件信息列表。"""
    outputs = history_item.get("outputs") or {}
    files = []
    for _node_id, node_output in outputs.items():
        if isinstance(node_output, dict):
            for img in node_output.get("images") or []:
                if isinstance(img, dict) and img.get("filename"):
                    files.append({
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                    })
    return files


def _organize_output_images(
    base_dir: str | None,
    project_name: str,
    output_files: list[dict[str, str]],
) -> int:
    """
    将 ComfyUI 输出图片复制到统一输出目录 {OUTPUT_BASE_DIR}/{project_name}/{YYYYMMDD}/。
    文件重命名为 {项目名}_{时间戳}_{原名}.png 避免覆盖。
    保留原始文件不动（ComfyUI 预览和 Assets 面板需要读取它们）。
    返回处理的文件数。
    """
    if not base_dir or not output_files:
        return 0

    source_output = Path(base_dir) / "output"
    if not source_output.exists():
        return 0

    from app.settings.config import settings

    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in project_name).strip()

    output_base = Path(settings.OUTPUT_BASE_DIR)
    if not output_base.is_absolute():
        output_base = Path(settings.BASE_DIR) / output_base
    unified_dir = output_base / safe_name / date_str
    unified_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    processed = 0
    for finfo in output_files:
        fname = finfo["filename"]
        subfolder = finfo.get("subfolder", "")
        src = source_output / subfolder / fname if subfolder else source_output / fname
        if not src.exists() or not src.is_file():
            continue

        stem = Path(fname).stem
        suffix = Path(fname).suffix
        new_name = f"{safe_name}_{ts}_{stem}{suffix}"
        dst = unified_dir / new_name

        idx = 1
        while dst.exists():
            new_name = f"{safe_name}_{ts}_{stem}_{idx}{suffix}"
            dst = unified_dir / new_name
            idx += 1

        try:
            shutil.copy2(str(src), str(dst))
            processed += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] copy file failed: {src} -> {dst} ({e})")

    return processed


async def sync_once(*, max_items: int = 200) -> int:
    """
    从所有在线服务拉取最新 history，并将新 prompt_id 写入 generation_logs。
    同时统计每次生成的图片数量，并将输出图片移动到统一输出目录。

    为什么不会丢失记录：
    - ComfyUI /history 保存在内存中，是**累积**的完整执行记录，不是只保留最近 N 秒的
    - 即使图像在 1 秒内生成完毕，history 中的记录也会一直保留直到 ComfyUI 进程重启
    - max_items=200 表示每次最多拉取 200 条，足以覆盖两次轮询间隔内的所有执行
    - 已同步的 prompt_id 通过数据库去重（unique_together），不会重复写入
    - 唯一可能丢失的场景：ComfyUI 进程崩溃重启，内存中的 history 被清空
      → 但此时节点的 platform callback 已经缓存了 image_count 作为补充

    返回本次新增的日志条数。
    """
    services = await ComfyUIService.filter(status="online").all()
    created = 0
    for s in services:
        if not s.comfy_url:
            continue
        try:
            history = await _fetch_history(s.comfy_url, max_items=max_items)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] history fetch failed: {s.comfy_url} ({e})")
            continue

        project = await Project.filter(id=s.project_id).first()
        project_name = project.name if project else f"project_{s.project_id}"

        from app.api.internal.comfy import get_callback_cache
        cb_data = get_callback_cache(s.project_id)

        for prompt_id, item in history.items():
            if not prompt_id:
                continue
            exists = await GenerationLog.filter(project_id=s.project_id, prompt_id=str(prompt_id)).exists()
            if exists:
                continue

            item_dict = item if isinstance(item, dict) else {}
            status_str, extra = _map_status(item_dict)
            image_count = _count_output_images(item_dict)
            output_files = _collect_output_files(item_dict)

            if cb_data and cb_data.get("image_count", 0) > image_count:
                image_count = cb_data["image_count"]

            if output_files and s.base_dir:
                _organize_output_images(s.base_dir, project_name, output_files)

            details = {
                "prompt_id": str(prompt_id),
                "comfy_url": s.comfy_url,
                "image_count": image_count,
                "output_files": [f["filename"] for f in output_files],
                **extra,
            }
            await GenerationLog.create(
                user_id=s.user_id,
                project_id=s.project_id,
                timestamp=datetime.now(),
                status=status_str,
                prompt_id=str(prompt_id),
                concurrent_id=None,
                image_count=image_count,
                details=details,
            )
            created += 1
    return created


async def sync_loop(stop_event: asyncio.Event, *, interval_seconds: int = 10) -> None:
    """
    后台轮询 ComfyUI history 并自动写入 generation_logs。
    """
    if interval_seconds <= 0:
        logger.warning("[ComfyUI] history sync disabled (interval<=0)")
        return

    while not stop_event.is_set():
        try:
            n = await sync_once()
            if n:
                logger.info(f"[ComfyUI] history synced: +{n}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ComfyUI] history sync error: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
