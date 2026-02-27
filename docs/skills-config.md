# Skills 技能框架

## 概述

Skills（技能）是预配置的 LLM 提示词模板，用户可以在 AI 聊天窗口中一键调用。每个技能封装了特定的系统提示词和用户消息模板，使得常见任务（翻译、代码审查、文本摘要等）无需手动编写提示词。

## 架构

```
┌─────────────┐     GET /api/chat/skills      ┌──────────────────┐
│  前端 Chat   │ ─────────────────────────────→ │  Skills API      │
│  Window      │                                │  (chat.py)       │
│              │  POST /api/chat/skills/:id/run │                  │
│              │ ─────────────────────────────→ │                  │
│              │ ←── SSE stream (token/done) ── │                  │
└─────────────┘                                └──────┬───────────┘
                                                      │
                                               ┌──────▼───────────┐
                                               │ skills_config.py │
                                               │ (技能定义)        │
                                               └──────────────────┘
```

## 内置技能列表

| ID | 名称 | 分类 | 说明 |
|----|------|------|------|
| `translate` | 智能翻译 | 语言 | 中英文互译，保持专业术语准确 |
| `code_review` | 代码审查 | 开发 | 审查代码，发现 bug、性能问题和改进建议 |
| `summarize` | 文本摘要 | 写作 | 将长文本提炼为结构化摘要 |
| `data_analysis` | 数据分析助手 | 数据 | 分析数据并给出洞察和可视化建议 |
| `workflow_helper` | ComfyUI 工作流助手 | AI生成 | 帮助理解和优化 ComfyUI 工作流参数 |

## 添加自定义技能

在 `vue-fastapi-admin-main/app/services/skills_config.py` 的 `SKILLS` 列表中追加新的 `SkillConfig`：

```python
SkillConfig(
    id="my_skill",              # 唯一标识，用于 API 路由
    name="我的技能",             # 前端显示名称
    icon="ri:star-line",        # 图标（Remix Icon 格式）
    description="简短说明",      # 前端展示的描述文字
    system_prompt="你是...",     # 系统提示词，定义 AI 角色和行为
    user_prompt_template="请处理：\n\n{input}",  # {input} 会被替换为用户输入
    category="自定义",           # 分类标签
)
```

### SkillConfig 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | str | 是 | 唯一标识符，用于 API 路由匹配 |
| `name` | str | 是 | 前端显示的技能名称 |
| `icon` | str | 是 | 图标标识（Remix Icon 命名规范） |
| `description` | str | 是 | 技能的简要说明 |
| `system_prompt` | str | 是 | 发送给 LLM 的系统提示词 |
| `user_prompt_template` | str | 是 | 用户消息模板，`{input}` 为占位符 |
| `category` | str | 否 | 分类标签，默认 "通用" |
| `parameters` | dict | 否 | 预留扩展参数 |

## API 参考

### 获取技能列表

```
GET /api/chat/skills
Authorization: <token>
```

**响应示例：**

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "id": "translate",
      "name": "智能翻译",
      "icon": "ri:translate-2",
      "description": "中英文互译，保持专业术语准确",
      "category": "语言"
    }
  ]
}
```

### 执行技能

```
POST /api/chat/skills/{skill_id}/run
Authorization: <token>
Content-Type: application/json

{
  "content": "用户输入内容",
  "model_provider": "openai",     // 可选，使用默认提供商
  "model_name": "gpt-4",          // 可选，使用默认模型
  "temperature": 0.7,             // 可选
  "max_tokens": 2000              // 可选
}
```

**响应：SSE 流**

```
data: {"type": "token", "content": "翻译"}
data: {"type": "token", "content": "结果"}
data: {"type": "done", "content": ""}
```

错误时返回：

```
data: {"type": "error", "content": "技能执行失败: ..."}
```

## 前端使用

在 AI 聊天窗口的输入区域，点击魔术棒图标（✨）打开技能选择面板。选择技能后，输入框上方会显示当前激活的技能标签。发送消息时，系统会自动调用对应技能的 API 端点，完成后技能状态自动清除。

### 前端 API 函数

```typescript
import { fetchSkills, streamSkill } from '@/api/chat'

// 获取技能列表
const skills = await fetchSkills()

// 执行技能（SSE 流式）
const controller = await streamSkill(
  'translate',
  { content: '你好世界' },
  (token) => { /* 处理 token */ },
  () => { /* 完成回调 */ },
  (err) => { /* 错误回调 */ }
)

// 取消执行
controller.abort()
```

## 配置示例

### 添加一个 SQL 生成技能

```python
SkillConfig(
    id="sql_gen",
    name="SQL 生成器",
    icon="ri:database-2-line",
    description="根据自然语言描述生成 SQL 查询",
    system_prompt=(
        "你是一位 SQL 专家。根据用户的自然语言描述生成正确的 SQL 查询语句。"
        "默认使用 PostgreSQL 语法。输出时先给出 SQL，再简要解释查询逻辑。"
    ),
    user_prompt_template="请根据以下描述生成 SQL 查询：\n\n{input}",
    category="开发",
)
```

### 添加一个邮件撰写技能

```python
SkillConfig(
    id="email_writer",
    name="邮件撰写",
    icon="ri:mail-line",
    description="根据要点生成专业的商务邮件",
    system_prompt="你是一位商务沟通专家。根据用户提供的要点，撰写专业、礼貌的商务邮件。支持中英文。",
    user_prompt_template="请根据以下要点撰写邮件：\n\n{input}",
    category="写作",
)
```
