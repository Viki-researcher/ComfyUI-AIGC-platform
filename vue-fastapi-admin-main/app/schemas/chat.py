from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)
    model_provider: str = Field(default="", max_length=50)
    model_name: str = Field(default="", max_length=100)
    system_prompt: str = Field(default="")


class SessionUpdate(BaseModel):
    title: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    system_prompt: str | None = None


class ChatSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)
    model_provider: str = Field(default="")
    model_name: str = Field(default="")
    temperature: float | None = None
    max_tokens: int | None = None
    document_ids: list[int] = Field(default_factory=list, description="RAG 关联的文档 ID")
    enable_rag: bool = Field(default=False, description="是否启用 RAG 检索")
    enable_agent: bool = Field(default=False, description="是否启用 Agent 工具调用")
