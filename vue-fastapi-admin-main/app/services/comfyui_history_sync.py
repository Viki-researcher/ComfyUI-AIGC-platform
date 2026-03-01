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
    """将 ComfyUI 输出图片移动到 {base_dir}/output/{project_name}/{YYYYMMDD}/ 目录。返回移动的文件数。"""
    if not base_dir or not output_files:
        return 0

    source_output = Path(base_dir) / "output"
    if not source_output.exists():
        return 0

    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in project_name).strip()
    target_dir = source_output / safe_name / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for finfo in output_files:
        fname = finfo["filename"]
        subfolder = finfo.get("subfolder", "")
        src = source_output / subfolder / fname if subfolder else source_output / fname
        if src.exists() and src.is_file():
            dst = target_dir / fname
            if dst.exists():
                continue
            try:
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[ComfyUI] move file failed: {src} -> {dst} ({e})")
    return moved


async def sync_once(*, max_items: int = 50) -> int:
    """
    从所有在线服务拉取最新 history，并将新 prompt_id 写入 generation_logs。
    同时统计每次生成的图片数量并组织输出文件。
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
