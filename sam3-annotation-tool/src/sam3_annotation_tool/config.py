"""
SAM3 Annotation Tool 模型路径配置

从平台统一配置读取：环境变量 SAM3_MODEL_PATH 或 ANNOTATION_SAM3_MODEL_PATH。
由平台 .env.platform / vue-fastapi-admin-main/.env 中的 ANNOTATION_SAM3_MODEL_PATH 传入。
"""
import os

_DEFAULT_MODEL_ID = "facebook/sam3"


def get_model_path() -> str:
    """
    获取 SAM3 模型加载路径。

    优先级：
    1. 环境变量 SAM3_MODEL_PATH（直接运行标注工具时）
    2. 环境变量 ANNOTATION_SAM3_MODEL_PATH（平台启动时传入）
    3. 默认 "facebook/sam3"（从 HuggingFace Hub 加载）

    本地路径需为 HuggingFace 格式目录（含 config.json、preprocessor_config.json 等）。
    """
    for key in ("SAM3_MODEL_PATH", "ANNOTATION_SAM3_MODEL_PATH"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return _DEFAULT_MODEL_ID
