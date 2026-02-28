from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

import httpx

from app.log import logger
from app.models.platform import AnnotationService
from app.services.comfyui_manager import stop_pid
from app.settings.config import settings


def _parse_port_range(s: str) -> Tuple[int, int]:
    left, right = s.split("-", 1)
    a, b = int(left.strip()), int(right.strip())
    if a <= 0 or b <= 0 or a > b:
        raise ValueError(f"invalid ANNOTATION_PORT_RANGE: {s}")
    return a, b


def _pick_free_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free port available in annotation range")


def _derive_internal_host(listen: str) -> str:
    if settings.ANNOTATION_INTERNAL_HOST:
        return settings.ANNOTATION_INTERNAL_HOST
    if listen in ("0.0.0.0", "::", "[::]"):
        return "127.0.0.1"
    return listen


def _read_log_tail(log_path: Path, lines: int = 15) -> str:
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:]).strip()
    except Exception:
        return "(无法读取日志)"


async def is_healthy(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(url)
            return r.status_code == 200
    except Exception:
        return False


async def start_annotation_instance(user_id: int, project_id: int) -> dict:
    tool_path = Path(settings.ANNOTATION_TOOL_PATH).expanduser().resolve()
    if not tool_path.exists():
        raise RuntimeError(f"ANNOTATION_TOOL_PATH not found: {tool_path}")
    if not (tool_path / "app.py").exists():
        raise RuntimeError(f"app.py not found in: {tool_path}")

    port_start, port_end = _parse_port_range(settings.ANNOTATION_PORT_RANGE)
    port = _pick_free_port(port_start, port_end)

    listen = settings.ANNOTATION_LISTEN
    internal_host = _derive_internal_host(listen)
    annotation_url = f"http://{internal_host}:{port}"

    log_dir = Path(settings.ANNOTATION_LOG_DIR).expanduser()
    if not log_dir.is_absolute():
        log_dir = Path(settings.BASE_DIR) / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"annotation_u{user_id}_p{project_id}_{port}.log"

    env = os.environ.copy()
    env["GRADIO_SERVER_PORT"] = str(port)
    env["GRADIO_SERVER_NAME"] = listen

    python_exec = "python3"
    uv_path = os.popen("which uv 2>/dev/null").read().strip()
    if uv_path:
        cmd = [uv_path, "run", "python", "app.py"]
    else:
        cmd = [python_exec, "app.py"]

    logger.info(f"[Annotation] starting: {' '.join(cmd)} on port {port}")
    with open(log_path, "ab", buffering=0) as f:
        proc = subprocess.Popen(
            cmd,
            cwd=str(tool_path),
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

    timeout = max(5, int(settings.ANNOTATION_STARTUP_TIMEOUT_SECONDS))
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = _read_log_tail(log_path, 15)
            raise RuntimeError(f"标注工具进程异常退出 (code={proc.returncode}):\n{tail}")
        if await is_healthy(annotation_url):
            return {
                "port": port,
                "annotation_url": annotation_url,
                "pid": proc.pid,
                "log_path": str(log_path),
            }
        await asyncio.sleep(1)

    stop_pid(proc.pid)
    tail = _read_log_tail(log_path, 15)
    raise RuntimeError(f"标注工具启动超时:\n{tail}")


async def ensure_annotation_service(user_id: int, project_id: int) -> AnnotationService:
    existing = await AnnotationService.filter(project_id=project_id).first()
    if existing and existing.status == "online" and existing.annotation_url:
        if await is_healthy(existing.annotation_url):
            return existing

    if existing and existing.pid:
        try:
            stop_pid(int(existing.pid))
        except Exception as e:
            logger.warning(f"[Annotation] stop old pid failed: {existing.pid} ({e})")

    info = await start_annotation_instance(user_id=user_id, project_id=project_id)

    if existing:
        await existing.update_from_dict(
            dict(
                port=info["port"],
                status="online",
                annotation_url=info["annotation_url"],
                pid=info["pid"],
                log_path=info["log_path"],
                start_time=datetime.now(),
            )
        ).save()
        return existing

    return await AnnotationService.create(
        user_id=user_id,
        project_id=project_id,
        port=info["port"],
        status="online",
        annotation_url=info["annotation_url"],
        pid=info["pid"],
        log_path=info["log_path"],
        start_time=datetime.now(),
    )
