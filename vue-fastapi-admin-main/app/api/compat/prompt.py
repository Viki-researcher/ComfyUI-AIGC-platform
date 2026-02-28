from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependency import DependPermission
from app.schemas.base import Success

router = APIRouter(prefix="/prompt", tags=["Prompt助手模块"])

STYLE_TEMPLATES = {
    "写实摄影": "professional photography, ultra realistic, 8k resolution, sharp focus, natural lighting, DSLR quality",
    "动漫风格": "anime style, vibrant colors, cel shading, detailed lineart, studio ghibli inspired",
    "概念艺术": "concept art, digital painting, artstation trending, matte painting, cinematic composition",
    "产品渲染": "product photography, studio lighting, white background, commercial quality, 3D render",
    "人像特写": "portrait photography, headshot, professional studio lighting, shallow depth of field, bokeh",
    "场景建筑": "architectural visualization, exterior/interior design, photorealistic rendering, golden hour",
    "科幻未来": "sci-fi concept, futuristic design, cyberpunk aesthetic, neon lighting, volumetric fog",
    "水彩插画": "watercolor painting, soft colors, artistic illustration, hand-painted texture, paper texture",
}

QUALITY_BOOSTERS = [
    "masterpiece", "best quality", "highly detailed", "professional",
    "4k", "8k resolution", "sharp focus", "award winning"
]

NEGATIVE_COMMON = (
    "low quality, worst quality, blurry, deformed, disfigured, "
    "bad anatomy, bad proportions, extra limbs, watermark, text, signature"
)


class PromptRequest(BaseModel):
    description: str = Field(..., description="用户需求描述（中文或英文）")
    style: str = Field("写实摄影", description="风格模板")
    enhance: bool = Field(True, description="是否添加质量增强词")


class PromptResponse(BaseModel):
    positive: str
    negative: str
    style_used: str
    tips: list[str]


@router.post("/generate", summary="智能Prompt生成", dependencies=[DependPermission])
async def generate_prompt(req: PromptRequest):
    style_suffix = STYLE_TEMPLATES.get(req.style, STYLE_TEMPLATES["写实摄影"])

    parts = [req.description.strip()]
    parts.append(style_suffix)
    if req.enhance:
        parts.extend(QUALITY_BOOSTERS[:4])

    positive = ", ".join(parts)
    negative = NEGATIVE_COMMON

    tips = [
        f"已应用「{req.style}」风格模板",
        "建议在 ComfyUI 中配合 ControlNet 使用以获得更精确的结果",
        "可在正面提示词末尾添加具体的画面细节描述",
    ]
    if req.enhance:
        tips.append("已添加质量增强词，适合高分辨率输出")

    return Success(data=PromptResponse(
        positive=positive,
        negative=negative,
        style_used=req.style,
        tips=tips,
    ).model_dump())


@router.get("/styles", summary="获取可用风格列表", dependencies=[DependPermission])
async def list_styles():
    return Success(data=[
        {"key": k, "preview": v[:60] + "..."} for k, v in STYLE_TEMPLATES.items()
    ])
