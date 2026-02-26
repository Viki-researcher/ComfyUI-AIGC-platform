"""
Token 用量追踪服务

记录每次 LLM 调用的 token 消耗，提供按用户、日期范围的用量汇总查询。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tortoise.expressions import Q

from app.log import logger
from app.models.chat import TokenUsage


async def record_usage(
    user_id: int,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """记录一次 LLM 调用的 token 用量。"""
    await TokenUsage.create(
        user_id=user_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    logger.debug(
        f"[Quota] user={user_id} provider={provider} model={model} "
        f"prompt={prompt_tokens} completion={completion_tokens}"
    )


async def get_user_usage_summary(
    user_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """查询指定用户的 token 用量汇总。"""
    q = Q(user_id=user_id)
    if start_date:
        q &= Q(created_at__gte=datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        fmt = "%Y-%m-%d %H:%M:%S" if " " in end_date else "%Y-%m-%d"
        q &= Q(created_at__lte=datetime.strptime(end_date, fmt))

    rows = await TokenUsage.filter(q).all()
    total_prompt = sum(r.prompt_tokens for r in rows)
    total_completion = sum(r.completion_tokens for r in rows)

    by_model: dict[str, dict[str, int]] = {}
    for r in rows:
        key = f"{r.provider}/{r.model}"
        if key not in by_model:
            by_model[key] = {"prompt_tokens": 0, "completion_tokens": 0, "count": 0}
        by_model[key]["prompt_tokens"] += r.prompt_tokens
        by_model[key]["completion_tokens"] += r.completion_tokens
        by_model[key]["count"] += 1

    return {
        "user_id": user_id,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "call_count": len(rows),
        "by_model": by_model,
    }


async def get_all_users_usage(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """查询所有用户的 token 用量汇总。"""
    q = Q()
    if start_date:
        q &= Q(created_at__gte=datetime.strptime(start_date, "%Y-%m-%d"))
    if end_date:
        q &= Q(created_at__lte=datetime.strptime(end_date, "%Y-%m-%d"))

    rows = await TokenUsage.filter(q).all()

    user_map: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r.user_id not in user_map:
            user_map[r.user_id] = {
                "user_id": r.user_id,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "call_count": 0,
            }
        user_map[r.user_id]["total_prompt_tokens"] += r.prompt_tokens
        user_map[r.user_id]["total_completion_tokens"] += r.completion_tokens
        user_map[r.user_id]["call_count"] += 1

    result = []
    for uid, data in sorted(user_map.items()):
        data["total_tokens"] = data["total_prompt_tokens"] + data["total_completion_tokens"]
        result.append(data)

    return result
