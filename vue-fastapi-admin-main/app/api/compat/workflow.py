"""
Workflow API — ComfyUI 工作流模板、AI 生成与提交
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependency import AuthControl
from app.log import logger
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.services.comfyui_workflow_agent import (
    WORKFLOW_TEMPLATES,
    _generate_workflow,
    _modify_workflow_params,
    _submit_workflow,
)

router = APIRouter(prefix="/workflow", tags=["工作流"])


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------

class GenerateWorkflowRequest(BaseModel):
    description: str = Field(..., description="自然语言描述")


class SubmitWorkflowRequest(BaseModel):
    workflow: dict[str, Any] = Field(..., description="ComfyUI 工作流 JSON")
    comfy_url: str = Field(..., description="ComfyUI 实例地址")


class ModifyWorkflowRequest(BaseModel):
    workflow: dict[str, Any] = Field(..., description="已有工作流 JSON")
    modification: str = Field(..., description="修改描述")


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.get("/templates", summary="获取工作流模板列表")
async def list_templates(_user: User = Depends(AuthControl.is_authed)):
    templates = []
    for key, tpl in WORKFLOW_TEMPLATES.items():
        templates.append({
            "name": key,
            "display_name": tpl["display_name"],
            "description": tpl["description"],
            "workflow": tpl["workflow"],
        })
    return Success(data=templates)


@router.post("/generate", summary="AI 生成工作流")
async def generate_workflow(body: GenerateWorkflowRequest, user: User = Depends(AuthControl.is_authed)):
    import json

    result_str = await _generate_workflow(user_id=user.id, description=body.description)
    result = json.loads(result_str)

    if "error" in result:
        logger.warning(f"[WorkflowAPI] generate failed: {result['error']}")
        return Fail(msg=result["error"])

    return Success(data=result)


@router.post("/submit", summary="提交工作流到 ComfyUI")
async def submit_workflow(body: SubmitWorkflowRequest, user: User = Depends(AuthControl.is_authed)):
    import json

    result_str = await _submit_workflow(
        user_id=user.id,
        workflow=body.workflow,
        comfy_url=body.comfy_url,
    )
    result = json.loads(result_str)

    if "error" in result:
        logger.warning(f"[WorkflowAPI] submit failed: {result['error']}")
        return Fail(msg=result["error"])

    return Success(data=result)


@router.put("/modify", summary="AI 修改工作流参数")
async def modify_workflow(body: ModifyWorkflowRequest, user: User = Depends(AuthControl.is_authed)):
    import json

    result_str = await _modify_workflow_params(
        user_id=user.id,
        workflow=body.workflow,
        modification=body.modification,
    )
    result = json.loads(result_str)

    if "error" in result:
        logger.warning(f"[WorkflowAPI] modify failed: {result['error']}")
        return Fail(msg=result["error"])

    return Success(data=result)
