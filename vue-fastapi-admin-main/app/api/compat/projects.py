from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependPermission
from app.log import logger
from app.models import User
from app.models.platform import AnnotationService, ComfyUIService, Project
from app.services.comfyui_manager import restart_comfyui_service, stop_pid
from app.services.annotation_manager import ensure_annotation_service
from app.schemas.base import Fail, Success
from app.schemas.platform import OpenAnnotationOut, OpenComfyOut, ProjectCreate, ProjectUpdate
from app.settings.config import settings

router = APIRouter(prefix="/projects", tags=["项目模块"])


def _now_str(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _get_public_comfy_url(*, port: int, request: Request) -> str:
    """
    返回给前端打开的 ComfyUI/标注地址（局域网访问时需使用主机 IP，避免 localhost 导致其他机器无法访问）。
    - 优先使用 COMFYUI_PUBLIC_BASE_URL（或 ANNOTATION 同理，本函数共用）
    - 否则从请求头推导（X-Forwarded-Host / Host）
    - 若推导结果为 localhost/127.0.0.1，则使用 PLATFORM_PUBLIC_HOST
    """
    base = (settings.COMFYUI_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if base:
        if "://" not in base:
            base = f"http://{base}"
        from urllib.parse import urlparse

        u = urlparse(base)
        if not u.hostname:
            pass
        else:
            scheme = u.scheme or "http"
            return f"{scheme}://{u.hostname}:{port}"

    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",", 1)[0].strip()
    host = forwarded_host or (request.headers.get("host") or "").strip() or (request.url.hostname or "")
    proto = (request.headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip() or request.url.scheme or "http"

    hostname = ""
    if host.startswith("[") and "]" in host:
        hostname = host[1 : host.find("]")]
    else:
        hostname = host.split(":", 1)[0]
    hostname = hostname or "127.0.0.1"

    # 若为 localhost，且配置了 PLATFORM_PUBLIC_HOST，则使用主机 IP（支持局域网其他机器访问）
    if hostname in ("127.0.0.1", "localhost", "::1") and (settings.PLATFORM_PUBLIC_HOST or "").strip():
        hostname = (settings.PLATFORM_PUBLIC_HOST or "").strip().split(":", 1)[0]

    return f"{proto}://{hostname}:{port}"


@router.post("", summary="新建项目", dependencies=[DependPermission])
async def create_project(req_in: ProjectCreate):
    user_id = CTX_USER_ID.get()

    exists = await Project.filter(code=req_in.code).exists()
    if exists:
        return Fail(code=400, msg="项目号已存在")

    obj = await Project.create(
        name=req_in.name,
        code=req_in.code,
        note=req_in.note,
        target_count=req_in.target_count,
        owner_user_id=user_id,
    )
    owner = await User.filter(id=user_id).first()

    return Success(
        data={
            "id": obj.id,
            "name": obj.name,
            "code": obj.code,
            "note": obj.note,
            "owner_user_id": obj.owner_user_id,
            "owner_user_name": owner.username if owner else "",
            "target_count": obj.target_count,
            "generated_count": 0,
            "comfy_status": "stopped",
            "annotation_status": "stopped",
            "create_time": _now_str(obj.created_at),
            "update_time": _now_str(obj.updated_at),
        }
    )


@router.get("", summary="项目列表", dependencies=[DependPermission])
async def list_projects(
    name: str | None = Query(None, description="项目名称"),
    code: str | None = Query(None, description="项目号"),
):
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if code:
        q &= Q(code__contains=code)

    rows = await Project.filter(q).order_by("-id").all()
    owner_ids = list({int(p.owner_user_id) for p in rows if p.owner_user_id is not None})
    owner_rows = await User.filter(id__in=owner_ids).values("id", "username") if owner_ids else []
    owner_map = {int(r["id"]): r["username"] for r in owner_rows}

    from app.models.platform import GenerationLog
    from tortoise.functions import Sum
    project_ids = [p.id for p in rows]
    gen_counts = {}
    for pid in project_ids:
        agg = await GenerationLog.filter(project_id=pid, status="成功").annotate(total=Sum("image_count")).values("total")
        gen_counts[pid] = agg[0]["total"] or 0 if agg else 0

    comfy_map = {}
    ann_map = {}
    for svc in await ComfyUIService.filter(project_id__in=project_ids).all():
        comfy_map[svc.project_id] = svc.status
    for svc in await AnnotationService.filter(project_id__in=project_ids).all():
        ann_map[svc.project_id] = svc.status

    def _output_dir_name(name: str) -> str:
        return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()

    data = [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "note": p.note,
            "owner_user_id": p.owner_user_id,
            "owner_user_name": owner_map.get(int(p.owner_user_id), ""),
            "target_count": p.target_count,
            "generated_count": gen_counts.get(p.id, 0),
            "comfy_status": comfy_map.get(p.id, "stopped"),
            "annotation_status": ann_map.get(p.id, "stopped"),
            "output_dir": _output_dir_name(p.name),
            "create_time": _now_str(p.created_at),
            "update_time": _now_str(p.updated_at),
        }
        for p in rows
    ]
    return Success(data=data)


@router.put("/{project_id}", summary="更新项目", dependencies=[DependPermission])
async def update_project(project_id: int, req_in: ProjectUpdate):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")
    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    update_dict = req_in.model_dump(exclude_unset=True)
    if update_dict:
        await project.update_from_dict(update_dict).save()
    owner = await User.filter(id=project.owner_user_id).first()

    return Success(
        data={
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "note": project.note,
            "owner_user_id": project.owner_user_id,
            "owner_user_name": owner.username if owner else "",
            "create_time": _now_str(project.created_at),
            "update_time": _now_str(project.updated_at),
        }
    )


@router.delete("/{project_id}", summary="删除项目", dependencies=[DependPermission])
async def delete_project(project_id: int):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")
    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    # 1) 停止 ComfyUI 服务进程并删除服务记录
    svc = await ComfyUIService.filter(project_id=project_id).first()
    if svc and svc.pid:
        try:
            stop_pid(int(svc.pid))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Project] stop ComfyUI pid={svc.pid} failed: {e}")
    await ComfyUIService.filter(project_id=project_id).delete()

    # 2) 停止标注服务进程并删除服务记录
    ann_svc = await AnnotationService.filter(project_id=project_id).first()
    if ann_svc and ann_svc.pid:
        try:
            stop_pid(int(ann_svc.pid))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[Project] stop Annotation pid={ann_svc.pid} failed: {e}")
    await AnnotationService.filter(project_id=project_id).delete()

    # 注意：保留 GenerationLog 和 output 图片目录，不做清理

    # 3) 删除项目记录
    await Project.filter(id=project_id).delete()
    return Success(msg="Deleted")


@router.post("/{project_id}/open_comfy", summary="打开/启动 ComfyUI 服务", dependencies=[DependPermission])
async def open_comfy(project_id: int, request: Request):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")

    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    from app.models.platform import GenerationLog
    from tortoise.functions import Sum
    agg = await GenerationLog.filter(project_id=project_id, status="成功").annotate(total=Sum("image_count")).values("total")
    gen_count = agg[0]["total"] or 0 if agg else 0
    if project.target_count and gen_count >= project.target_count:
        return Fail(
            code=400,
            msg=f"已达到目标生成数量上限（{gen_count}/{project.target_count}），请通过编辑项目修改目标数量后继续"
        )

    existing = await ComfyUIService.filter(project_id=project_id).first()
    if existing and existing.user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    try:
        svc = await restart_comfyui_service(user_id=user_id, project_id=project_id)
    except Exception as e:  # noqa: BLE001
        return Fail(code=500, msg=f"启动 ComfyUI 失败：{e}")

    public_url = _get_public_comfy_url(port=int(svc.port), request=request)
    return Success(data=OpenComfyOut(comfy_url=public_url).model_dump())


@router.post("/{project_id}/open_annotation", summary="打开/启动 数据标注服务", dependencies=[DependPermission])
async def open_annotation(project_id: int, request: Request):
    user_id = CTX_USER_ID.get()
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")

    if project.owner_user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    existing = await AnnotationService.filter(project_id=project_id).first()
    if existing and existing.user_id != user_id:
        return Fail(code=403, msg="无操作权限")

    try:
        svc = await ensure_annotation_service(user_id=user_id, project_id=project_id)
    except Exception as e:  # noqa: BLE001
        return Fail(code=500, msg=f"启动标注服务失败：{e}")

    public_url = _get_public_comfy_url(port=int(svc.port), request=request)
    return Success(data=OpenAnnotationOut(annotation_url=public_url).model_dump())


@router.get("/{project_id}/images", summary="列出项目生成图片", dependencies=[DependPermission])
async def list_project_images(project_id: int):
    project = await Project.filter(id=project_id).first()
    if not project:
        return Fail(code=404, msg="项目不存在")

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in project.name).strip()
    output_base = Path(settings.OUTPUT_BASE_DIR)
    if not output_base.is_absolute():
        output_base = Path(settings.BASE_DIR) / output_base
    project_dir = output_base / safe_name

    files = []
    if project_dir.exists():
        for f in sorted(project_dir.rglob("*"), reverse=True):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                rel = f.relative_to(project_dir)
                files.append({
                    "name": f.name,
                    "path": str(rel),
                    "size": f.stat().st_size,
                    "date": f.parent.name,
                })
    return Success(data={"project_name": project.name, "dir": safe_name, "files": files, "total": len(files)})


@router.get("/{project_id}/browse", summary="浏览项目图片目录（HTML）")
async def browse_project_images(project_id: int):
    """返回项目输出目录的 HTML 文件列表页面（无图片预览）。"""
    from fastapi.responses import HTMLResponse

    project = await Project.filter(id=project_id).first()
    if not project:
        return HTMLResponse("<h3>项目不存在</h3>", status_code=404)

    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in project.name).strip()
    output_base = Path(settings.OUTPUT_BASE_DIR)
    if not output_base.is_absolute():
        output_base = Path(settings.BASE_DIR) / output_base
    project_dir = output_base / safe_name

    if not project_dir.exists():
        return HTMLResponse(f"<h3>目录不存在：{safe_name}/</h3><p>该项目尚未生成任何图片。</p>")

    rows = []
    for sub in sorted(project_dir.iterdir(), reverse=True):
        if sub.is_dir():
            img_files = sorted(sub.iterdir())
            for f in img_files:
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    size_kb = f.stat().st_size / 1024
                    rel = f.relative_to(project_dir)
                    url = f"/output/{safe_name}/{rel}"
                    rows.append(
                        f'<tr><td>{sub.name}</td>'
                        f'<td><a href="{url}" target="_blank">{f.name}</a></td>'
                        f'<td>{size_kb:.1f} KB</td></tr>'
                    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{project.name} — 图像目录</title>
<style>
body{{font-family:system-ui,sans-serif;margin:20px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:6px 12px;text-align:left}}
th{{background:#f5f7fa}}
a{{color:#409eff;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style></head>
<body><h2>{project.name} — 图像目录</h2>
<p>共 {len(rows)} 个文件</p>
<table><tr><th>日期</th><th>文件名</th><th>大小</th></tr>
{''.join(rows)}
</table></body></html>"""
    return HTMLResponse(html)

