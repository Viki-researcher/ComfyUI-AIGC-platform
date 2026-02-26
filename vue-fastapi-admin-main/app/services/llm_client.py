"""
LLM Client Abstraction Layer

统一封装多种大模型提供商的调用，全部基于 OpenAI-compatible 接口协议。
支持: OpenAI / DeepSeek / 通义千问 / Ollama / vLLM / 任意兼容端点。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.log import logger
from app.settings.config import settings

# 预置提供商默认 base_url
_PROVIDER_DEFAULTS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "tongyi": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "ollama": "http://127.0.0.1:11434/v1",
}


@dataclass
class LLMProviderConfig:
    name: str
    display_name: str = ""
    api_key: str = ""
    base_url: str = ""
    models: list[str] = field(default_factory=list)
    default_model: str = ""


def get_provider_configs() -> list[LLMProviderConfig]:
    """从 settings 构建可用的提供商配置列表。"""
    configs: list[LLMProviderConfig] = []

    # 1. 从默认配置构建主提供商
    if settings.LLM_PROVIDER:
        base_url = settings.LLM_API_BASE_URL or _PROVIDER_DEFAULTS.get(settings.LLM_PROVIDER, "")
        configs.append(
            LLMProviderConfig(
                name=settings.LLM_PROVIDER,
                display_name=settings.LLM_PROVIDER.title(),
                api_key=settings.LLM_API_KEY,
                base_url=base_url,
                models=[settings.LLM_MODEL] if settings.LLM_MODEL else [],
                default_model=settings.LLM_MODEL,
            )
        )

    # 2. 从 LLM_PROVIDERS_JSON 追加额外提供商
    try:
        extra = json.loads(settings.LLM_PROVIDERS_JSON) if settings.LLM_PROVIDERS_JSON else []
        for item in extra:
            if isinstance(item, dict) and item.get("name"):
                name = item["name"]
                configs.append(
                    LLMProviderConfig(
                        name=name,
                        display_name=item.get("display_name", name.title()),
                        api_key=item.get("api_key", ""),
                        base_url=item.get("base_url", _PROVIDER_DEFAULTS.get(name, "")),
                        models=item.get("models", []),
                        default_model=item.get("default_model", ""),
                    )
                )
    except (json.JSONDecodeError, TypeError):
        logger.warning("[LLM] LLM_PROVIDERS_JSON 解析失败，忽略额外提供商")

    return configs


def _resolve_config(provider: str = "", model: str = "") -> tuple[LLMProviderConfig, str]:
    """根据 provider/model 参数查找配置。"""
    configs = get_provider_configs()
    if not configs:
        raise ValueError("未配置任何 LLM 提供商，请设置 LLM_PROVIDER 和 LLM_API_KEY")

    target = provider or settings.LLM_PROVIDER
    for cfg in configs:
        if cfg.name == target:
            resolved_model = model or cfg.default_model or settings.LLM_MODEL
            return cfg, resolved_model

    cfg = configs[0]
    resolved_model = model or cfg.default_model or settings.LLM_MODEL
    return cfg, resolved_model


def _build_client(cfg: LLMProviderConfig) -> AsyncOpenAI:
    api_key = cfg.api_key or "ollama"
    return AsyncOpenAI(api_key=api_key, base_url=cfg.base_url, timeout=120)


async def chat_completion_stream(
    messages: list[dict],
    provider: str = "",
    model: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> AsyncGenerator[str, None]:
    """流式对话补全，yield 每一段增量文本。"""
    cfg, resolved_model = _resolve_config(provider, model)
    client = _build_client(cfg)

    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    max_tok = max_tokens or settings.LLM_MAX_TOKENS

    logger.info(f"[LLM] stream → provider={cfg.name} model={resolved_model}")

    stream = await client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=temp,
        max_tokens=max_tok,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content


async def chat_completion(
    messages: list[dict],
    provider: str = "",
    model: str = "",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """非流式对话补全，返回完整文本。"""
    cfg, resolved_model = _resolve_config(provider, model)
    client = _build_client(cfg)

    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    max_tok = max_tokens or settings.LLM_MAX_TOKENS

    logger.info(f"[LLM] completion → provider={cfg.name} model={resolved_model}")

    resp = await client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=temp,
        max_tokens=max_tok,
        stream=False,
    )
    return resp.choices[0].message.content or ""


async def generate_embedding(text: str) -> list[float]:
    """生成文本嵌入向量（用于 RAG）。"""
    emb_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    emb_base = settings.EMBEDDING_API_BASE_URL or settings.LLM_API_BASE_URL or _PROVIDER_DEFAULTS.get(settings.LLM_PROVIDER, "")
    emb_model = settings.EMBEDDING_MODEL

    if not emb_key and settings.LLM_PROVIDER != "ollama":
        raise ValueError("未配置 EMBEDDING_API_KEY，无法生成嵌入向量")

    client = AsyncOpenAI(api_key=emb_key or "ollama", base_url=emb_base, timeout=60)
    resp = await client.embeddings.create(model=emb_model, input=text)
    return resp.data[0].embedding
