"""
Agent 执行引擎 — LLM + Function Calling 循环

通过 OpenAI SDK 的 tool_calls 机制实现多轮工具调用：
1. 将用户消息 + 工具定义发送给 LLM
2. 若 LLM 返回 tool_calls，逐一执行并将结果追加到上下文
3. 重新调用 LLM，直到模型直接给出文本回复或达到最大迭代次数
4. 全程通过 SSE 格式 yield 事件流
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

from app.log import logger
from app.services.agent_tools import execute_tool, get_tool_definitions
from app.services.llm_client import _build_client, _resolve_config

MAX_ITERATIONS = 5


async def run_agent_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    provider: str = "",
    model: str = "",
    user_id: int = 0,
) -> AsyncGenerator[str, None]:
    """
    Agent 流式执行循环。

    Yields:
        SSE data 行（JSON 字符串），事件类型包括:
        - {"type": "token",       "content": "..."}
        - {"type": "tool_call",   "name": "...", "arguments": "..."}
        - {"type": "tool_result", "name": "...", "result": "..."}
        - {"type": "done"}
        - {"type": "error",       "content": "..."}
    """
    cfg, resolved_model = _resolve_config(provider, model)
    client = _build_client(cfg)

    tool_defs = tools if tools is not None else get_tool_definitions()

    logger.info(
        f"[Agent] 启动执行循环 provider={cfg.name} model={resolved_model} "
        f"tools={len(tool_defs)} user_id={user_id}"
    )

    for iteration in range(MAX_ITERATIONS):
        try:
            response = await client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                tools=tool_defs if tool_defs else None,
                temperature=0.7,
                max_tokens=4096,
            )
        except Exception as exc:
            logger.error(f"[Agent] LLM 调用失败: {exc}")
            yield _sse({"type": "error", "content": f"模型调用失败: {str(exc)[:200]}"})
            yield _sse({"type": "done"})
            return

        choice = response.choices[0]
        message = choice.message

        # 如果 LLM 有 tool_calls，逐一执行
        if message.tool_calls:
            # 将 assistant 消息（含 tool_calls）追加到上下文
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                func_name = tc.function.name
                raw_args = tc.function.arguments

                yield _sse({"type": "tool_call", "name": func_name, "arguments": raw_args})

                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}

                result = await execute_tool(func_name, args, user_id)

                yield _sse({"type": "tool_result", "name": func_name, "result": result})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # 继续下一轮循环，让 LLM 根据工具结果回答
            continue

        # LLM 直接给出文本回复 — 逐段 yield
        content = message.content or ""
        if content:
            yield _sse({"type": "token", "content": content})

        yield _sse({"type": "done"})
        return

    # 达到最大迭代次数仍有 tool_calls，强制结束
    logger.warning(f"[Agent] 达到最大迭代次数 {MAX_ITERATIONS}，强制结束")
    yield _sse({"type": "token", "content": "（已达到最大工具调用轮次，自动结束）"})
    yield _sse({"type": "done"})


def _sse(data: dict) -> str:
    """将字典序列化为 SSE data 行格式。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
