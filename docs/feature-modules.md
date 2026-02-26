# 菲特数据生成平台 — 功能模块文档

## 目录

- [一阶段功能](#一阶段功能)
  - [1.1 对话体验优化](#11-对话体验优化)
  - [1.2 多模态能力](#12-多模态能力)
  - [1.3 模型管理](#13-模型管理)
  - [2.1 Agent 框架](#21-agent-框架)
  - [2.3 数据分析 Agent](#23-数据分析-agent)
  - [3. RAG 增强](#3-rag-增强)
  - [6.3 配额与计费仪表板](#63-配额与计费仪表板)
  - [8. Docker Compose 部署](#8-docker-compose-部署)
- [二阶段功能](#二阶段功能)
  - [4. ComfyUI 工作流可视化编辑器](#4-comfyui-工作流可视化编辑器)
  - [2.2 ComfyUI 工作流 Agent](#22-comfyui-工作流-agent)

---

## 一阶段功能

### 1.1 对话体验优化

#### Markdown 渲染

AI 回复内容支持完整的 Markdown 语法渲染，包括：
- 标题（H1-H6）
- 有序/无序列表
- 代码块（带语法高亮）
- 表格
- 加粗/斜体/链接
- 引用块

**技术实现**：
- 使用 `marked` 库解析 Markdown 为 HTML
- 使用 `highlight.js` 对代码块进行语法高亮（支持 100+ 语言）
- 使用 `DOMPurify` 对生成的 HTML 进行 XSS 安全过滤
- 用户消息保持纯文本显示，仅 AI 回复使用 Markdown 渲染

**相关文件**：
- `art-design-pro/src/components/core/layouts/art-chat-window/index.vue` — `renderMarkdown()` 函数

#### 代码高亮

技术类回复中的代码块自动高亮显示：
- 自动检测编程语言
- 暗色背景 + 等宽字体
- 支持 Python、JavaScript、TypeScript、JSON、SQL、Bash 等语言

---

### 1.2 多模态能力

#### 图片输入

用户可以在对话中发送图片给视觉大模型：

**使用方式**：
1. 点击输入框旁的图片上传按钮（📷）
2. 或直接粘贴剪贴板中的图片（Ctrl+V）
3. 图片上传后显示缩略图预览
4. 发送消息时自动携带图片

**技术实现**：
- 前端：图片上传至 `/api/chat/images/upload`，获取 URL 后插入消息
- 后端：将图片 base64 编码，构建 OpenAI 视觉格式消息
- 支持模型：GPT-4o、Qwen-VL 等支持 vision 的模型

**API**：
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/images/upload` | 上传图片 |
| GET | `/api/chat/images/{filename}` | 获取图片 |

#### 图片预览

AI 回复中包含的图片 URL 自动渲染为内嵌图片（`<img>` 标签），支持：
- HTTP/HTTPS 图片 URL 自动检测
- Markdown 格式图片 `![alt](url)`
- 最大宽度限制，防止撑破布局

#### 文件预览

上传的 RAG 文档支持在线预览：
- **PDF**：在新标签页中打开
- **图片**：内嵌预览
- **文本/Markdown**：在弹窗中显示内容

---

### 1.3 模型管理

#### 前端实时模型切换

在对话窗口顶部显示当前模型标签，点击可展开模型选择面板：

**功能**：
- 显示所有已配置的 LLM 提供商及其模型列表
- 按提供商分组展示（如 OpenAI / 各大模型厂商 / Ollama）
- 选择模型后立即更新当前会话配置
- 切换后的新消息使用新模型回复

**技术实现**：
- 前端使用 `ElPopover` 弹出层
- 调用 `GET /api/chat/providers` 获取可用模型
- 选择后调用 `PUT /api/chat/sessions/{id}` 更新会话

---

### 2.1 Agent 框架

#### 基础架构

平台内置了 Function Calling 型 Agent 框架，支持 LLM 自动调用工具：

**执行流程**：
```
用户消息 → LLM 判断是否需要工具 → 调用工具 → 获取结果 → 再次调用 LLM → 返回最终回复
```

**核心组件**：

| 组件 | 文件 | 说明 |
|------|------|------|
| 工具注册中心 | `app/services/agent_tools.py` | `ToolRegistry` 类，管理工具定义与执行 |
| Agent 执行器 | `app/services/agent_executor.py` | `run_agent_stream()` 函数，实现 LLM + 工具调用循环 |

**SSE 事件类型**：

| 事件类型 | 说明 |
|---------|------|
| `token` | LLM 生成的文本片段 |
| `tool_call` | LLM 决定调用工具（含工具名和参数） |
| `tool_result` | 工具执行结果 |
| `done` | 对话完成 |
| `error` | 错误信息 |

#### 内置工具集

| 工具名 | 说明 | 参数 |
|--------|------|------|
| `list_projects` | 查询项目列表 | 无 |
| `query_generation_logs` | 查询生成日志 | project_id, status, start_date, end_date |
| `get_server_stats` | 获取服务器 CPU/内存/磁盘状态 | 无 |
| `analyze_anomalies` | 检测生成失败率异常 | days (分析天数) |
| `export_report_excel` | 导出 Excel 统计报表 | dimension, start_date, end_date |

**使用方式**：在对话窗口中开启 "Agent" 模式开关，然后正常提问即可。

---

### 2.3 数据分析 Agent

通过 Agent 框架的内置工具实现智能数据分析：

#### 日志分析
```
用户: "分析一下本月的生成成功率"
Agent: 调用 query_generation_logs → 统计成功/失败数 → 生成分析报告
```

#### 异常检测
```
用户: "最近有没有异常"
Agent: 调用 analyze_anomalies → 对比近7天与前7天失败率 → 输出异常告警
```

#### 报表生成
```
用户: "导出本周各项目的生成统计"
Agent: 调用 export_report_excel → 生成 Excel 文件 → 返回下载链接
```

---

### 3. RAG 增强

#### 引用追踪

AI 回复中标注引用来源：
- RAG 检索结果通过 SSE `rag_citations` 事件发送到前端
- 每条引用包含：文档名称、片段内容、匹配分数
- 前端在 AI 回复下方显示"参考来源"卡片

#### 多模态 RAG

支持图片文件用于 RAG：
- 图片上传后自动使用视觉模型生成描述文本
- 描述文本参与分块和检索
- 支持格式：PNG、JPG、GIF、WebP

#### ComfyUI 文档 RAG

自动索引 ComfyUI 相关文档：
- 扫描 ComfyUI 仓库中的 `.md`、`.txt`、`.py` 文件
- 创建系统级文档（user_id=0）
- 用户问 ComfyUI 相关问题时自动检索

**API**：
```
POST /api/chat/index-comfyui-docs  (TODO: 待添加触发端点)
```

#### 表格理解

支持结构化数据文件：
- **CSV**：解析为 Markdown 表格后分块
- **Excel**（xlsx/xls）：读取第一个工作表，转为 Markdown 表格
- 表格数据保持列对齐，便于 LLM 理解

---

### 6.3 配额与计费仪表板

#### Token 用量追踪

自动记录每次 LLM 调用的 Token 消耗：

**数据模型**：
```
TokenUsage:
  - user_id: 用户ID
  - provider: 提供商
  - model: 模型名称
  - prompt_tokens: 输入 Token 数
  - completion_tokens: 输出 Token 数
  - created_at: 记录时间
```

**API**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/chat/usage` | 获取当前用户的用量统计 |
| GET | `/api/chat/usage/all` | 获取所有用户用量（仅管理员） |

**返回数据**：
```json
{
  "total_prompt_tokens": 15000,
  "total_completion_tokens": 8000,
  "total_tokens": 23000,
  "by_model": [
    {"provider": "openai", "model": "gpt-4o-mini", "prompt": 10000, "completion": 5000}
  ]
}
```

---

### 8. Docker Compose 部署

#### 一键启动

```bash
# 1. 复制环境变量配置
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY 等配置

# 2. 启动所有服务
docker compose up -d

# 3. 访问
# 前端: http://localhost:3006
# 后端: http://localhost:9999
# 默认账号: admin / 123456
```

#### 服务架构

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `postgres` | postgres:16-alpine | 5432 | PostgreSQL 数据库 |
| `backend` | 自建 (Python 3.11) | 9999 | FastAPI 后端 |
| `frontend` | 自建 (Node → Nginx) | 3006 | Vue 前端 |

#### 开发模式

仅启动数据库，前端和后端本地运行：

```bash
docker compose -f docker-compose.dev.yml up -d
# 然后按照 AGENTS.md 中的说明启动前后端
```

**相关文件**：
- `docker-compose.yml` — 生产部署
- `docker-compose.dev.yml` — 开发模式
- `.env.example` — 环境变量模板
- `art-design-pro/Dockerfile` — 前端构建
- `art-design-pro/nginx.conf` — Nginx 配置
- `vue-fastapi-admin-main/Dockerfile` — 后端构建（已存在）

---

## 二阶段功能

### 4. ComfyUI 工作流可视化编辑器

#### 功能概述

在平台内嵌入简化版的 ComfyUI 工作流编辑器，无需打开 ComfyUI 原生界面即可编辑和提交工作流。

#### 界面布局

```
┌────────────┬─────────────────────┬──────────────┐
│ 模板库      │   JSON 编辑器       │  参数面板     │
│            │                     │              │
│ · txt2img  │  {                  │ 提示词:       │
│ · img2img  │    "nodes": {...}   │ [________]   │
│            │    ...              │ 分辨率:       │
│            │  }                  │ [512] x [512]│
│            │                     │ 步数: [20]   │
│            │                     │ CFG: [7]     │
│            │                     │ 种子: [随机]  │
│            │                     │ 采样器:      │
│            │                     │ [euler ▼]    │
└────────────┴─────────────────────┴──────────────┘
                    [AI 生成]  [提交到 ComfyUI]
```

#### 功能清单

- 加载预置工作流模板（txt2img、img2img）
- JSON 编辑器直接编辑工作流
- 参数面板自动提取关键参数
- 修改参数自动更新 JSON
- AI 生成：通过自然语言描述生成工作流 JSON
- 提交：将工作流发送到运行中的 ComfyUI 实例

#### 路由

菜单路径：`数据生成平台 → 工作流编辑器`
URL：`/platform/workflow`

**相关文件**：
- `art-design-pro/src/views/platform/workflow-editor/index.vue`
- `art-design-pro/src/api/workflow.ts`
- `art-design-pro/src/router/modules/platform.ts`

---

### 2.2 ComfyUI 工作流 Agent

#### 自然语言生图

在对话中通过自然语言描述生成需求，Agent 自动生成 ComfyUI 工作流并提交执行：

```
用户: "帮我生成一张赛博朋克风格的城市夜景，分辨率 1024x768"
Agent:
  1. 调用 generate_workflow 工具 → 生成工作流 JSON
  2. 调用 submit_workflow 工具 → 提交到 ComfyUI
  3. 返回提交结果和 prompt_id
```

#### 工作流调参

支持通过对话修改已有工作流的参数：

```
用户: "把图片分辨率改成 1024x1024，步数改为 30"
Agent:
  1. 调用 modify_workflow_params 工具 → 修改参数
  2. 返回修改后的工作流 JSON
```

#### Agent 工具列表

| 工具名 | 说明 |
|--------|------|
| `list_workflow_templates` | 列出可用的工作流模板 |
| `generate_workflow` | 根据自然语言描述生成工作流 JSON |
| `modify_workflow_params` | 修改工作流参数 |
| `submit_workflow` | 提交工作流到 ComfyUI 实例执行 |

**API**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workflow/templates` | 获取模板列表 |
| POST | `/api/workflow/generate` | AI 生成工作流 |
| POST | `/api/workflow/submit` | 提交工作流执行 |
| PUT | `/api/workflow/modify` | AI 修改工作流参数 |

**相关文件**：
- `vue-fastapi-admin-main/app/services/comfyui_workflow_agent.py`
- `vue-fastapi-admin-main/app/api/compat/workflow.py`

---

## 技术架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ AI 对话   │ │ 工作流    │ │ 数据统计  │ │ 服务器监控 │  │
│  │ 窗口      │ │ 编辑器   │ │ 仪表板   │ │           │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       └─────────────┴────────────┴──────────────┘        │
│                          │ REST API + SSE                 │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                    后端 (FastAPI)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Chat API │ │Workflow  │ │ Agent    │ │ RAG       │  │
│  │ (SSE)    │ │ API      │ │ Executor │ │ Service   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       │             │            │              │         │
│  ┌────┴─────────────┴────────────┴──────────────┴─────┐  │
│  │              LLM Client (OpenAI SDK)                │  │
│  │    多提供商支持 (OpenAI-compatible 协议)               │  │
│  └────────────────────────────────────────────────────┘  │
│       │                                                   │
│  ┌────┴───────────────────────────────────────────────┐  │
│  │         Tortoise ORM (PostgreSQL / SQLite)          │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────┐
│                    ComfyUI Engine                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  ComfyUI 实例 (按需启动，每用户/每项目独立)         │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

*文档版本：v2.0*
*更新日期：2026-02-26*
