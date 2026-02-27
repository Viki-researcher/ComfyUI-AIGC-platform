"""
ComfyUI Workflow Agent — 工作流模板管理与 AI 辅助生成

提供以下 Agent 工具：
- list_workflow_templates: 列出可用的工作流模板
- generate_workflow: 根据自然语言描述，使用 LLM 生成 ComfyUI 工作流 JSON
- modify_workflow_params: 使用 LLM 修改已有工作流的参数
- submit_workflow: 将工作流提交到运行中的 ComfyUI 实例
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.log import logger
from app.services.agent_tools import _registry
from app.services.llm_client import chat_completion

# ---------------------------------------------------------------------------
# 工作流模板
# ---------------------------------------------------------------------------

WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "txt2img": {
        "name": "txt2img",
        "display_name": "文生图 (Text-to-Image)",
        "description": "基础文本到图像生成工作流，支持正向/反向提示词、分辨率、采样步数等参数",
        "workflow": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7.0,
                    "denoise": 1.0,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "seed": 42,
                    "steps": 20,
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"batch_size": 1, "height": 512, "width": 512},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "a beautiful landscape painting, masterpiece, best quality",
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "ugly, blurry, low quality",
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "txt2img", "images": ["8", 0]},
            },
        },
    },
    "img2img": {
        "name": "img2img",
        "display_name": "图生图 (Image-to-Image)",
        "description": "图像到图像生成工作流，加载输入图像并在其基础上进行修改生成",
        "workflow": {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "input.png"},
            },
            "2": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["1", 0], "vae": ["4", 2]},
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7.0,
                    "denoise": 0.75,
                    "latent_image": ["2", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "seed": 42,
                    "steps": 20,
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "a beautiful painting, high quality",
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": "ugly, blurry, low quality",
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "img2img", "images": ["8", 0]},
            },
        },
    },
}

# ---------------------------------------------------------------------------
# LLM 系统提示词
# ---------------------------------------------------------------------------

_GENERATE_SYSTEM_PROMPT = """\
你是 ComfyUI 工作流 JSON 生成专家。用户会用自然语言描述他们想要的图像生成需求，
你需要返回一个合法的 ComfyUI workflow JSON（API 格式）。

ComfyUI workflow JSON 格式说明：
- 顶层是一个对象，键为节点 ID（字符串数字），值为节点定义
- 每个节点有 class_type 和 inputs 两个字段
- inputs 中引用其他节点用 ["节点ID", 输出索引] 格式

常用节点类型：
- CheckpointLoaderSimple: 加载模型检查点
- CLIPTextEncode: 文本编码（正/反向提示词）
- EmptyLatentImage: 空潜空间图像（设置分辨率）
- KSampler: 采样器（steps, cfg, seed, sampler_name, scheduler, denoise）
- VAEDecode: VAE 解码
- SaveImage: 保存图像
- LoadImage: 加载图像

以下是一个基础的 txt2img 模板供参考：
```json
{TEMPLATE_REF}
```

请根据用户描述生成工作流 JSON。只返回 JSON，不要包含其他文字。"""

_MODIFY_SYSTEM_PROMPT = """\
你是 ComfyUI 工作流参数修改专家。用户会给你一个已有的 ComfyUI 工作流 JSON 和
一段修改描述，你需要根据描述修改对应参数并返回完整的修改后 JSON。

只返回修改后的完整 JSON，不要包含其他文字。"""


# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------

async def _list_workflow_templates(user_id: int, **_kwargs: Any) -> str:
    """列出可用的工作流模板。"""
    data = []
    for key, tpl in WORKFLOW_TEMPLATES.items():
        data.append({
            "name": key,
            "display_name": tpl["display_name"],
            "description": tpl["description"],
        })
    return json.dumps({"templates": data, "total": len(data)}, ensure_ascii=False)


async def _generate_workflow(
    user_id: int,
    description: str = "",
    **_kwargs: Any,
) -> str:
    """根据自然语言描述使用 LLM 生成 ComfyUI 工作流 JSON。"""
    if not description:
        return json.dumps({"error": "请提供工作流描述"}, ensure_ascii=False)

    template_ref = json.dumps(WORKFLOW_TEMPLATES["txt2img"]["workflow"], indent=2, ensure_ascii=False)
    system_prompt = _GENERATE_SYSTEM_PROMPT.replace("{TEMPLATE_REF}", template_ref)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": description},
    ]

    try:
        result = await chat_completion(messages=messages, temperature=0.3)
        cleaned = result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        workflow = json.loads(cleaned)
        logger.info(f"[WorkflowAgent] 成功生成工作流, 节点数: {len(workflow)}")
        return json.dumps({"workflow": workflow}, ensure_ascii=False)
    except json.JSONDecodeError:
        logger.warning("[WorkflowAgent] LLM 返回的 JSON 无法解析")
        return json.dumps({"error": "生成的工作流 JSON 格式无效，请重试", "raw": result[:500]}, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"[WorkflowAgent] 生成工作流失败: {exc}")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


async def _modify_workflow_params(
    user_id: int,
    workflow: dict | None = None,
    modification: str = "",
    **_kwargs: Any,
) -> str:
    """使用 LLM 修改已有工作流的参数。"""
    if not workflow:
        return json.dumps({"error": "请提供工作流 JSON"}, ensure_ascii=False)
    if not modification:
        return json.dumps({"error": "请提供修改描述"}, ensure_ascii=False)

    workflow_str = json.dumps(workflow, indent=2, ensure_ascii=False)
    messages = [
        {"role": "system", "content": _MODIFY_SYSTEM_PROMPT},
        {"role": "user", "content": f"工作流 JSON:\n```json\n{workflow_str}\n```\n\n修改要求: {modification}"},
    ]

    try:
        result = await chat_completion(messages=messages, temperature=0.2)
        cleaned = result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        modified = json.loads(cleaned)
        logger.info(f"[WorkflowAgent] 成功修改工作流, 节点数: {len(modified)}")
        return json.dumps({"workflow": modified}, ensure_ascii=False)
    except json.JSONDecodeError:
        logger.warning("[WorkflowAgent] LLM 修改后的 JSON 无法解析")
        return json.dumps({"error": "修改后的工作流 JSON 格式无效，请重试", "raw": result[:500]}, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"[WorkflowAgent] 修改工作流失败: {exc}")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


async def _submit_workflow(
    user_id: int,
    workflow: dict | None = None,
    comfy_url: str = "",
    **_kwargs: Any,
) -> str:
    """将工作流提交到运行中的 ComfyUI 实例。"""
    if not workflow:
        return json.dumps({"error": "请提供工作流 JSON"}, ensure_ascii=False)
    if not comfy_url:
        return json.dumps({"error": "请提供 ComfyUI 实例地址"}, ensure_ascii=False)

    prompt_url = f"{comfy_url.rstrip('/')}/prompt"
    payload = {"prompt": workflow}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(prompt_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            prompt_id = data.get("prompt_id", "")
            logger.info(f"[WorkflowAgent] 工作流已提交, prompt_id={prompt_id}, url={prompt_url}")
            return json.dumps({"prompt_id": prompt_id, "status": "submitted"}, ensure_ascii=False)
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300] if exc.response else ""
        logger.error(f"[WorkflowAgent] 提交失败 HTTP {exc.response.status_code}: {body}")
        return json.dumps({"error": f"ComfyUI 返回错误: HTTP {exc.response.status_code}", "detail": body}, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"[WorkflowAgent] 提交工作流异常: {exc}")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 注册工具到全局注册表
# ---------------------------------------------------------------------------

_registry.register(
    name="list_workflow_templates",
    description="列出可用的 ComfyUI 工作流模板，包括 txt2img、img2img 等",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
    handler=_list_workflow_templates,
)

_registry.register(
    name="generate_workflow",
    description="根据自然语言描述，使用 AI 生成 ComfyUI 工作流 JSON。描述示例：'生成一张 1024x1024 的风景画，使用 30 步采样'",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "自然语言描述，说明想要生成的工作流"},
        },
        "required": ["description"],
    },
    handler=_generate_workflow,
)

_registry.register(
    name="modify_workflow_params",
    description="使用 AI 修改已有 ComfyUI 工作流的参数。例如：修改分辨率、步数、提示词等",
    parameters={
        "type": "object",
        "properties": {
            "workflow": {"type": "object", "description": "已有的工作流 JSON"},
            "modification": {"type": "string", "description": "修改描述，例如 '将分辨率改为 1024x1024'"},
        },
        "required": ["workflow", "modification"],
    },
    handler=_modify_workflow_params,
)

_registry.register(
    name="submit_workflow",
    description="将工作流 JSON 提交到运行中的 ComfyUI 实例执行",
    parameters={
        "type": "object",
        "properties": {
            "workflow": {"type": "object", "description": "要提交的工作流 JSON"},
            "comfy_url": {"type": "string", "description": "ComfyUI 实例的访问地址，例如 http://127.0.0.1:8200"},
        },
        "required": ["workflow", "comfy_url"],
    },
    handler=_submit_workflow,
)
