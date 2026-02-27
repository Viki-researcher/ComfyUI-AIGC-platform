"""
LLM Skills 配置 — 预设技能模板，用户可一键调用。

每个 Skill 包含:
- id: 唯一标识
- name: 显示名称
- icon: 图标标识
- description: 简要说明
- system_prompt: 系统提示词
- user_prompt_template: 用户消息模板，{input} 为用户输入
- category: 分类
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillConfig:
    id: str
    name: str
    icon: str
    description: str
    system_prompt: str
    user_prompt_template: str
    category: str = "通用"
    parameters: dict = field(default_factory=dict)


SKILLS: list[SkillConfig] = [
    SkillConfig(
        id="translate",
        name="智能翻译",
        icon="ri:translate-2",
        description="中英文互译，保持专业术语准确",
        system_prompt="你是一位专业翻译。如果输入是中文，翻译成英文；如果输入是英文，翻译成中文。保持专业术语准确，语句自然流畅。",
        user_prompt_template="请翻译以下内容：\n\n{input}",
        category="语言",
    ),
    SkillConfig(
        id="code_review",
        name="代码审查",
        icon="ri:code-s-slash-line",
        description="审查代码，发现 bug、性能问题和改进建议",
        system_prompt="你是一位资深软件工程师。请仔细审查用户提供的代码，指出：1) 潜在的 bug 2) 性能问题 3) 代码风格改进 4) 安全隐患。用中文回答，给出具体的修改建议。",
        user_prompt_template="请审查以下代码：\n\n```\n{input}\n```",
        category="开发",
    ),
    SkillConfig(
        id="summarize",
        name="文本摘要",
        icon="ri:file-text-line",
        description="将长文本提炼为结构化摘要",
        system_prompt="你是一位文本分析专家。请将用户提供的长文本提炼为结构化摘要，包含：1) 核心观点 2) 关键信息 3) 结论。控制在200字以内。",
        user_prompt_template="请对以下内容进行摘要：\n\n{input}",
        category="写作",
    ),
    SkillConfig(
        id="data_analysis",
        name="数据分析助手",
        icon="ri:bar-chart-box-line",
        description="分析数据并给出洞察和可视化建议",
        system_prompt="你是一位数据分析师。请分析用户提供的数据，给出：1) 关键发现 2) 数据趋势 3) 异常点 4) 可视化建议。如果数据是表格格式，先理解列含义。",
        user_prompt_template="请分析以下数据：\n\n{input}",
        category="数据",
    ),
    SkillConfig(
        id="workflow_helper",
        name="ComfyUI 工作流助手",
        icon="ri:flow-chart",
        description="帮助理解和优化 ComfyUI 工作流参数",
        system_prompt="你是 ComfyUI 专家。帮助用户理解 ComfyUI 工作流节点、参数含义，提供优化建议。当用户提供工作流 JSON 时，解释各节点的作用和参数含义。",
        user_prompt_template="{input}",
        category="AI生成",
    ),
]


def get_skills() -> list[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "icon": s.icon,
            "description": s.description,
            "category": s.category,
        }
        for s in SKILLS
    ]


def get_skill_by_id(skill_id: str) -> SkillConfig | None:
    for s in SKILLS:
        if s.id == skill_id:
            return s
    return None


def build_skill_messages(skill_id: str, user_input: str) -> list[dict] | None:
    skill = get_skill_by_id(skill_id)
    if not skill:
        return None
    return [
        {"role": "system", "content": skill.system_prompt},
        {"role": "user", "content": skill.user_prompt_template.replace("{input}", user_input)},
    ]
