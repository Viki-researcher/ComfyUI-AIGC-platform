"""
RAG (Retrieval-Augmented Generation) Service

支持文件上传 → 文本提取 → 分块 → 嵌入 → 检索 完整 Pipeline。
支持 txt / md / pdf / docx 文件类型。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from app.log import logger
from app.models.chat import ChatDocument, DocumentChunk
from app.settings.config import settings


# ─── 文本提取 ───────────────────────────────────────────

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """从文件提取纯文本。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = file_type.lower()

    if ext in ("txt", "md", "markdown", "text"):
        return path.read_text(encoding="utf-8", errors="replace")

    if ext == "pdf":
        return _extract_pdf(path)

    if ext in ("docx", "doc"):
        return _extract_docx(path)

    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ─── 文本分块 ───────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 0, overlap: int = 0) -> list[str]:
    """将文本按字符长度切分为多个块，支持重叠。"""
    if not chunk_size:
        chunk_size = settings.RAG_CHUNK_SIZE
    if not overlap:
        overlap = settings.RAG_CHUNK_OVERLAP

    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


# ─── 嵌入生成 & 存储 ──────────────────────────────────────

async def process_document(doc_id: int) -> None:
    """完整处理上传文档: 提取 → 分块 → 嵌入 → 存储。"""
    doc = await ChatDocument.get_or_none(id=doc_id)
    if not doc:
        return

    try:
        text = extract_text_from_file(doc.file_path, doc.file_type)
        if not text.strip():
            doc.status = "error"
            doc.error_msg = "文件内容为空"
            await doc.save()
            return

        chunks = chunk_text(text)
        logger.info(f"[RAG] doc={doc_id} extracted {len(chunks)} chunks")

        for idx, chunk_text_content in enumerate(chunks):
            embedding_json = ""
            try:
                from app.services.llm_client import generate_embedding
                emb = await generate_embedding(chunk_text_content[:2000])
                embedding_json = json.dumps(emb)
            except Exception as e:
                logger.warning(f"[RAG] embedding failed for chunk {idx}: {e}")

            await DocumentChunk.create(
                document_id=doc.id,
                content=chunk_text_content,
                chunk_index=idx,
                embedding=embedding_json,
            )

        doc.chunk_count = len(chunks)
        doc.status = "ready"
        await doc.save()
        logger.info(f"[RAG] doc={doc_id} processing complete, {len(chunks)} chunks stored")

    except Exception as e:
        logger.error(f"[RAG] doc={doc_id} processing failed: {e}")
        doc.status = "error"
        doc.error_msg = str(e)[:500]
        await doc.save()


# ─── 检索 ─────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = float(np.dot(va, vb))
    norm = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return dot / norm if norm > 0 else 0.0


async def retrieve_relevant_chunks(
    query: str,
    user_id: int,
    document_ids: list[int] | None = None,
    top_k: int = 0,
) -> list[dict]:
    """根据查询文本检索最相关的文档分块。"""
    if not top_k:
        top_k = settings.RAG_TOP_K

    # 生成查询嵌入
    try:
        from app.services.llm_client import generate_embedding
        query_emb = await generate_embedding(query[:2000])
    except Exception as e:
        logger.warning(f"[RAG] query embedding failed, falling back to keyword search: {e}")
        return await _keyword_search(query, user_id, document_ids, top_k)

    # 获取用户的所有文档块
    doc_filter = {"user_id": user_id, "status": "ready"}
    docs = await ChatDocument.filter(**doc_filter).values_list("id", flat=True)
    if document_ids:
        docs = [d for d in docs if d in document_ids]

    if not docs:
        return []

    chunks = await DocumentChunk.filter(document_id__in=docs).all()

    # 向量相似度排序
    scored: list[tuple[float, DocumentChunk]] = []
    for chunk in chunks:
        if not chunk.embedding:
            continue
        try:
            emb = json.loads(chunk.embedding)
            score = _cosine_similarity(query_emb, emb)
            scored.append((score, chunk))
        except (json.JSONDecodeError, ValueError):
            continue

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "score": round(score, 4),
        })
    return results


async def _keyword_search(
    query: str,
    user_id: int,
    document_ids: list[int] | None,
    top_k: int,
) -> list[dict]:
    """关键词回退搜索（当嵌入不可用时）。"""
    doc_filter = {"user_id": user_id, "status": "ready"}
    docs = await ChatDocument.filter(**doc_filter).values_list("id", flat=True)
    if document_ids:
        docs = [d for d in docs if d in document_ids]
    if not docs:
        return []

    chunks = await DocumentChunk.filter(document_id__in=docs).all()
    keywords = query.lower().split()

    scored = []
    for chunk in chunks:
        content_lower = chunk.content.lower()
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "content": c.content,
            "score": s,
        }
        for s, c in scored[:top_k]
    ]


def build_rag_context(chunks: list[dict]) -> str:
    """将检索到的分块构建为上下文文本。"""
    if not chunks:
        return ""
    parts = ["以下是从用户上传的文档中检索到的相关内容，请参考回答：", ""]
    for i, ch in enumerate(chunks, 1):
        parts.append(f"[文档片段 {i}]")
        parts.append(ch["content"])
        parts.append("")
    return "\n".join(parts)


def ensure_upload_dir() -> str:
    upload_dir = settings.RAG_UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir
