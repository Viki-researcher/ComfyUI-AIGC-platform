"""
Chat API — 大模型对话、会话管理、文件上传 & RAG
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.dependency import AuthControl
from app.log import logger
from app.models.admin import User
from app.models.chat import ChatDocument, ChatMessage, ChatSession, DocumentChunk
from app.schemas.base import Fail, Success
from app.schemas.chat import ChatSend, SessionCreate, SessionUpdate
from app.services.agent_executor import run_agent_stream
from app.services.llm_client import chat_completion_stream, get_provider_configs
from app.services.quota_service import get_all_users_usage, get_user_usage_summary
from app.services.rag_service import (
    build_rag_context,
    ensure_upload_dir,
    process_document,
    retrieve_relevant_chunks,
)
from app.settings.config import settings

router = APIRouter(prefix="/chat", tags=["AI对话"])

IMAGE_UPLOAD_DIR = Path("runtime/chat_uploads/images")
REPORTS_DIR = Path("runtime/reports")
IMAGE_PATTERN = re.compile(r"\[image:(.*?)\]")


# ─── 提供商 & 配置 ──────────────────────────────────────────

@router.get("/providers", summary="获取可用的 LLM 提供商列表")
async def list_providers(_user: User = Depends(AuthControl.is_authed)):
    configs = get_provider_configs()
    data = []
    for cfg in configs:
        data.append({
            "name": cfg.name,
            "display_name": cfg.display_name or cfg.name,
            "models": cfg.models,
            "default_model": cfg.default_model,
        })
    return Success(data=data)


# ─── 会话管理 ────────────────────────────────────────────

@router.post("/sessions", summary="新建对话会话")
async def create_session(body: SessionCreate, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.create(
        user_id=user.id,
        title=body.title,
        model_provider=body.model_provider or settings.LLM_PROVIDER,
        model_name=body.model_name or settings.LLM_MODEL,
        system_prompt=body.system_prompt or settings.LLM_SYSTEM_PROMPT,
    )
    return Success(data=await _session_dict(session))


@router.get("/sessions", summary="获取当前用户的会话列表")
async def list_sessions(user: User = Depends(AuthControl.is_authed)):
    sessions = await ChatSession.filter(user_id=user.id, is_deleted=False).order_by("-updated_at")
    data = [await _session_dict(s) for s in sessions]
    return Success(data=data)


@router.get("/sessions/{session_id}", summary="获取会话详情")
async def get_session(session_id: int, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.get_or_none(id=session_id, user_id=user.id, is_deleted=False)
    if not session:
        return Fail(msg="会话不存在")
    return Success(data=await _session_dict(session))


@router.put("/sessions/{session_id}", summary="更新会话信息")
async def update_session(session_id: int, body: SessionUpdate, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.get_or_none(id=session_id, user_id=user.id, is_deleted=False)
    if not session:
        return Fail(msg="会话不存在")
    if body.title is not None:
        session.title = body.title
    if body.model_provider is not None:
        session.model_provider = body.model_provider
    if body.model_name is not None:
        session.model_name = body.model_name
    if body.system_prompt is not None:
        session.system_prompt = body.system_prompt
    await session.save()
    return Success(data=await _session_dict(session))


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: int, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.get_or_none(id=session_id, user_id=user.id)
    if not session:
        return Fail(msg="会话不存在")
    session.is_deleted = True
    await session.save()
    return Success(msg="已删除")


# ─── 消息 ────────────────────────────────────────────────

@router.get("/sessions/{session_id}/messages", summary="获取会话消息列表")
async def list_messages(session_id: int, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.get_or_none(id=session_id, user_id=user.id, is_deleted=False)
    if not session:
        return Fail(msg="会话不存在")
    msgs = await ChatMessage.filter(session_id=session_id).order_by("created_at")
    data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.strftime(settings.DATETIME_FORMAT) if m.created_at else "",
        }
        for m in msgs
    ]
    return Success(data=data)


@router.post("/sessions/{session_id}/chat", summary="发送消息并获取流式回复 (SSE)")
async def send_message(session_id: int, body: ChatSend, user: User = Depends(AuthControl.is_authed)):
    session = await ChatSession.get_or_none(id=session_id, user_id=user.id, is_deleted=False)
    if not session:
        return Fail(msg="会话不存在")

    await ChatMessage.create(session_id=session_id, role="user", content=body.content)

    history = await ChatMessage.filter(session_id=session_id).order_by("created_at")
    messages = _build_messages(session, history, body)

    rag_citations: list[dict] = []

    if body.enable_rag and settings.RAG_ENABLED:
        try:
            chunks = await retrieve_relevant_chunks(body.content, user.id, body.document_ids or None)
            if chunks:
                rag_ctx = build_rag_context(chunks)
                messages.insert(1, {"role": "system", "content": rag_ctx})
                rag_citations = chunks
        except Exception as e:
            logger.warning(f"[Chat] RAG retrieval failed: {e}")

    provider = body.model_provider or session.model_provider
    model = body.model_name or session.model_name

    if body.enable_agent:
        async def agent_event_generator():
            if rag_citations:
                yield f"data: {json.dumps({'type': 'rag_citations', 'citations': rag_citations}, ensure_ascii=False)}\n\n"

            full_reply = ""
            try:
                async for sse_line in run_agent_stream(
                    messages=messages,
                    provider=provider,
                    model=model,
                    user_id=user.id,
                ):
                    yield sse_line
                    try:
                        line_data = sse_line.strip()
                        if line_data.startswith("data: "):
                            payload = json.loads(line_data[6:])
                            if payload.get("type") == "token":
                                full_reply += payload.get("content", "")
                    except (json.JSONDecodeError, ValueError):
                        pass

                if full_reply:
                    await ChatMessage.create(session_id=session_id, role="assistant", content=full_reply)

                user_msg_count = await ChatMessage.filter(session_id=session_id, role="user").count()
                if user_msg_count == 1 and session.title == "新对话":
                    session.title = body.content[:30] + ("..." if len(body.content) > 30 else "")
                    await session.save()

            except Exception as e:
                logger.error(f"[Chat] agent stream error: {e}")
                err_msg = f"Agent 调用失败: {str(e)[:200]}"
                yield f"data: {json.dumps({'type': 'error', 'content': err_msg}, ensure_ascii=False)}\n\n"

        return StreamingResponse(agent_event_generator(), media_type="text/event-stream")

    async def event_generator():
        if rag_citations:
            yield f"data: {json.dumps({'type': 'rag_citations', 'citations': rag_citations}, ensure_ascii=False)}\n\n"

        full_reply = ""
        try:
            async for token in chat_completion_stream(
                messages=messages,
                provider=provider,
                model=model,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
            ):
                full_reply += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

            await ChatMessage.create(session_id=session_id, role="assistant", content=full_reply)

            user_msg_count = await ChatMessage.filter(session_id=session_id, role="user").count()
            if user_msg_count == 1 and session.title == "新对话":
                session.title = body.content[:30] + ("..." if len(body.content) > 30 else "")
                await session.save()

            yield f"data: {json.dumps({'type': 'done', 'content': ''}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[Chat] stream error: {e}")
            err_msg = f"模型调用失败: {str(e)[:200]}"
            yield f"data: {json.dumps({'type': 'error', 'content': err_msg}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── 图片上传 & 服务 ──────────────────────────────────────

@router.post("/images/upload", summary="上传图片 (多模态)")
async def upload_image(file: UploadFile = File(...), _user: User = Depends(AuthControl.is_authed)):
    if not file.filename:
        return Fail(msg="文件名为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"jpg", "jpeg", "png", "gif", "webp"}
    if ext not in allowed:
        return Fail(msg=f"不支持的图片类型: {ext}，支持: {', '.join(sorted(allowed))}")

    IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = IMAGE_UPLOAD_DIR / safe_name

    content = await file.read()
    file_path.write_bytes(content)

    logger.info(f"[Chat] image uploaded: {safe_name} ({len(content)} bytes)")
    return Success(data={
        "url": f"/api/chat/images/{safe_name}",
        "filename": safe_name,
    })


@router.get("/images/{filename}", summary="获取上传的图片")
async def get_image(filename: str):
    file_path = IMAGE_UPLOAD_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return Fail(msg="图片不存在")
    return FileResponse(str(file_path))


# ─── 文档上传 & RAG ──────────────────────────────────────

@router.post("/documents/upload", summary="上传文档 (RAG)")
async def upload_document(file: UploadFile = File(...), user: User = Depends(AuthControl.is_authed)):
    if not file.filename:
        return Fail(msg="文件名为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"txt", "md", "pdf", "docx", "doc", "markdown", "text", "csv", "xlsx", "xls", "png", "jpg", "jpeg", "gif", "webp"}
    if ext not in allowed:
        return Fail(msg=f"不支持的文件类型: {ext}，支持: {', '.join(sorted(allowed))}")

    upload_dir = ensure_upload_dir()
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = await ChatDocument.create(
        user_id=user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        file_type=ext,
    )

    asyncio.create_task(_safe_process(doc.id))

    return Success(data={
        "id": doc.id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "file_type": doc.file_type,
        "status": doc.status,
    })


@router.get("/documents", summary="获取当前用户的文档列表")
async def list_documents(user: User = Depends(AuthControl.is_authed)):
    docs = await ChatDocument.filter(user_id=user.id).order_by("-created_at")
    data = [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "file_type": d.file_type,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "created_at": d.created_at.strftime(settings.DATETIME_FORMAT) if d.created_at else "",
        }
        for d in docs
    ]
    return Success(data=data)


@router.delete("/documents/{doc_id}", summary="删除文档")
async def delete_document(doc_id: int, user: User = Depends(AuthControl.is_authed)):
    doc = await ChatDocument.get_or_none(id=doc_id, user_id=user.id)
    if not doc:
        return Fail(msg="文档不存在")
    await DocumentChunk.filter(document_id=doc.id).delete()
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await doc.delete()
    return Success(msg="已删除")


@router.get("/documents/{doc_id}/preview", summary="预览文档内容")
async def preview_document(doc_id: int, user: User = Depends(AuthControl.is_authed)):
    doc = await ChatDocument.get_or_none(id=doc_id, user_id=user.id)
    if not doc:
        return Fail(msg="文档不存在")
    if not os.path.exists(doc.file_path):
        return Fail(msg="文件不存在")

    ext = doc.file_type.lower()

    if ext in ("pdf", "png", "jpg", "jpeg", "gif", "webp", "svg"):
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }
        return FileResponse(
            doc.file_path,
            media_type=mime_map.get(ext, "application/octet-stream"),
            filename=doc.filename,
        )

    try:
        with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(200000)
    except Exception:
        with open(doc.file_path, "rb") as f:
            content = f.read(200000).decode("utf-8", errors="replace")

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content)


# ─── 用量查询 ─────────────────────────────────────────────

@router.get("/usage", summary="获取当前用户的 Token 用量汇总")
async def get_usage(
    user: User = Depends(AuthControl.is_authed),
    start_date: str | None = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    data = await get_user_usage_summary(user.id, start_date, end_date)
    return Success(data=data)


@router.get("/usage/all", summary="获取所有用户的 Token 用量汇总 (管理员)")
async def get_all_usage(
    user: User = Depends(AuthControl.is_authed),
    start_date: str | None = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    if not user.is_superuser:
        return Fail(msg="权限不足，仅管理员可查看")
    data = await get_all_users_usage(start_date, end_date)
    return Success(data=data)


# ─── 报告下载 ─────────────────────────────────────────────

@router.get("/reports/{filename}", summary="下载报告文件")
async def download_report(filename: str, _user: User = Depends(AuthControl.is_authed)):
    file_path = REPORTS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return Fail(msg="报告文件不存在")
    return FileResponse(str(file_path), filename=filename)


# ─── Helpers ─────────────────────────────────────────────

async def _safe_process(doc_id: int):
    try:
        await process_document(doc_id)
    except Exception as e:
        logger.error(f"[Chat] document processing error: {e}")


def _build_messages(session: ChatSession, history, body: ChatSend) -> list[dict]:
    """构建发送给 LLM 的消息列表，支持多模态图片消息。"""
    messages: list[dict] = []

    sys_prompt = session.system_prompt or settings.LLM_SYSTEM_PROMPT
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})

    recent = list(history)[-40:]
    for msg in recent:
        if msg.role == "user" and IMAGE_PATTERN.search(msg.content):
            messages.append({"role": "user", "content": _convert_multimodal(msg.content)})
        else:
            messages.append({"role": msg.role, "content": msg.content})

    return messages


def _convert_multimodal(text: str) -> list[dict]:
    """将含有 [image:URL] 标记的文本转换为 OpenAI 多模态格式。"""
    parts: list[dict] = []
    last_end = 0

    for match in IMAGE_PATTERN.finditer(text):
        if match.start() > last_end:
            plain = text[last_end:match.start()].strip()
            if plain:
                parts.append({"type": "text", "text": plain})

        image_url = match.group(1)
        if image_url.startswith("/api/chat/images/"):
            fname = image_url.split("/")[-1]
            local_path = IMAGE_UPLOAD_DIR / fname
            if local_path.exists():
                data = local_path.read_bytes()
                ext = local_path.suffix.lstrip(".").lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                        "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")
                b64 = base64.b64encode(data).decode()
                image_url = f"data:{mime};base64,{b64}"

        parts.append({"type": "image_url", "image_url": {"url": image_url}})
        last_end = match.end()

    trailing = text[last_end:].strip()
    if trailing:
        parts.append({"type": "text", "text": trailing})

    if not parts:
        parts.append({"type": "text", "text": text})

    return parts


async def _session_dict(session: ChatSession) -> dict:
    msg_count = await ChatMessage.filter(session_id=session.id).count()
    return {
        "id": session.id,
        "title": session.title,
        "model_provider": session.model_provider,
        "model_name": session.model_name,
        "system_prompt": session.system_prompt,
        "message_count": msg_count,
        "created_at": session.created_at.strftime(settings.DATETIME_FORMAT) if session.created_at else "",
        "updated_at": session.updated_at.strftime(settings.DATETIME_FORMAT) if session.updated_at else "",
    }
