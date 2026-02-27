# AI 对话功能配置文档

## 1. 功能概述

菲特数据生成平台集成了 AI 大模型对话功能，支持：

- **多用户独立会话**：每个用户拥有独立的对话会话列表和消息历史
- **多模型提供商**：兼容 OpenAI / DeepSeek / 通义千问 / Ollama 等所有 OpenAI-compatible API
- **本地模型部署**：支持通过 Ollama / vLLM 等部署本地开源模型（Qwen、DeepSeek 等）
- **流式响应**：基于 SSE (Server-Sent Events) 的实时流式输出
- **RAG 文档问答**：支持上传 txt/md/pdf/docx 文件，自动分块、嵌入、检索增强生成
- **灵活配置**：通过环境变量或 `.env` 文件配置所有参数

## 2. 快速开始

### 2.1 使用 OpenAI

```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
export LLM_MODEL=gpt-4o-mini
```

### 2.2 使用 DeepSeek

```bash
export LLM_PROVIDER=deepseek
export LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
export LLM_MODEL=deepseek-chat
```

### 2.3 使用通义千问

```bash
export LLM_PROVIDER=tongyi
export LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
export LLM_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export LLM_MODEL=qwen-plus
```

### 2.4 使用 Ollama (本地部署)

```bash
# 先安装并启动 Ollama: https://ollama.ai
# ollama pull qwen2.5:7b

export LLM_PROVIDER=ollama
export LLM_API_BASE_URL=http://127.0.0.1:11434/v1
export LLM_MODEL=qwen2.5:7b
# Ollama 不需要 API Key
```

### 2.5 使用 vLLM (本地高性能推理)

```bash
# vLLM 兼容 OpenAI API
export LLM_PROVIDER=custom
export LLM_API_BASE_URL=http://127.0.0.1:8000/v1
export LLM_API_KEY=EMPTY
export LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

## 3. 完整配置参考

所有配置项均通过环境变量设置（支持 `.env` 文件）。

### 3.1 LLM 基础配置

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|-------|------|
| `LLM_PROVIDER` | string | `openai` | 默认 LLM 提供商：`openai` / `deepseek` / `tongyi` / `ollama` / `custom` |
| `LLM_API_KEY` | string | `""` | API 密钥（Ollama 可留空） |
| `LLM_API_BASE_URL` | string | `""` | API 基地址（留空则使用提供商默认值） |
| `LLM_MODEL` | string | `gpt-4o-mini` | 默认模型名称 |
| `LLM_MAX_TOKENS` | int | `4096` | 最大生成 token 数 |
| `LLM_TEMPERATURE` | float | `0.7` | 生成温度 (0.0 - 2.0) |
| `LLM_SYSTEM_PROMPT` | string | `你是菲特数据生成平台的AI助手...` | 默认系统提示词 |

### 3.2 多提供商配置

通过 `LLM_PROVIDERS_JSON` 环境变量可以配置多个提供商，用户在前端可以切换：

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|-------|------|
| `LLM_PROVIDERS_JSON` | string (JSON) | `[]` | 额外提供商配置列表 |

示例：

```bash
export LLM_PROVIDERS_JSON='[
  {
    "name": "deepseek",
    "display_name": "DeepSeek",
    "api_key": "sk-xxx",
    "base_url": "https://api.deepseek.com/v1",
    "models": ["deepseek-chat", "deepseek-reasoner"],
    "default_model": "deepseek-chat"
  },
  {
    "name": "ollama",
    "display_name": "本地模型 (Ollama)",
    "api_key": "",
    "base_url": "http://127.0.0.1:11434/v1",
    "models": ["qwen2.5:7b", "llama3.1:8b", "deepseek-r1:8b"],
    "default_model": "qwen2.5:7b"
  }
]'
```

### 3.3 Embedding 配置 (RAG)

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|-------|------|
| `EMBEDDING_PROVIDER` | string | `""` | 嵌入提供商（留空则复用 LLM 配置） |
| `EMBEDDING_API_KEY` | string | `""` | 嵌入 API 密钥（留空则复用 `LLM_API_KEY`） |
| `EMBEDDING_API_BASE_URL` | string | `""` | 嵌入 API 基地址（留空则复用 `LLM_API_BASE_URL`） |
| `EMBEDDING_MODEL` | string | `text-embedding-3-small` | 嵌入模型名称 |

不同提供商的 Embedding 模型示例：
- OpenAI: `text-embedding-3-small`, `text-embedding-3-large`
- 通义千问: `text-embedding-v3`
- Ollama: `nomic-embed-text`, `bge-m3`

### 3.4 RAG 配置

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|-------|------|
| `RAG_ENABLED` | bool | `true` | 是否启用 RAG 功能 |
| `RAG_CHUNK_SIZE` | int | `500` | 文档分块大小（字符数） |
| `RAG_CHUNK_OVERLAP` | int | `50` | 分块重叠字符数 |
| `RAG_TOP_K` | int | `3` | 检索返回的最相关片段数量 |
| `RAG_UPLOAD_DIR` | string | `runtime/chat_uploads` | 文件上传存储目录 |

### 3.5 提供商预设 Base URL

| 提供商 | 默认 Base URL |
|--------|-------------|
| `openai` | `https://api.openai.com/v1` |
| `deepseek` | `https://api.deepseek.com/v1` |
| `tongyi` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `ollama` | `http://127.0.0.1:11434/v1` |
| `custom` | 必须通过 `LLM_API_BASE_URL` 指定 |

## 4. 架构说明

### 4.1 后端架构

```
vue-fastapi-admin-main/app/
├── api/compat/chat.py          # Chat API 路由 (SSE 流式)
├── models/chat.py              # 数据模型 (Session, Message, Document, Chunk)
├── schemas/chat.py             # Pydantic 请求/响应模型
├── services/
│   ├── llm_client.py           # LLM 统一调用层 (OpenAI SDK)
│   └── rag_service.py          # RAG Pipeline (解析/分块/嵌入/检索)
└── settings/config.py          # 配置项定义
```

### 4.2 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/chat/providers` | 获取可用的 LLM 提供商列表 |
| `POST` | `/api/chat/sessions` | 新建对话会话 |
| `GET` | `/api/chat/sessions` | 获取当前用户的会话列表 |
| `GET` | `/api/chat/sessions/{id}` | 获取会话详情 |
| `PUT` | `/api/chat/sessions/{id}` | 更新会话信息 |
| `DELETE` | `/api/chat/sessions/{id}` | 删除会话 |
| `GET` | `/api/chat/sessions/{id}/messages` | 获取消息历史 |
| `POST` | `/api/chat/sessions/{id}/chat` | 发送消息（SSE 流式响应） |
| `POST` | `/api/chat/documents/upload` | 上传文档 |
| `GET` | `/api/chat/documents` | 获取文档列表 |
| `DELETE` | `/api/chat/documents/{id}` | 删除文档 |

### 4.3 数据模型

```
ChatSession     ← 用户对话会话
  ├── user_id   → User
  ├── title
  ├── model_provider / model_name
  └── system_prompt

ChatMessage     ← 会话中的消息
  ├── session_id → ChatSession
  ├── role       (user / assistant / system)
  └── content

ChatDocument    ← 用户上传的 RAG 文档
  ├── user_id   → User
  ├── filename / file_path / file_type
  └── status    (processing / ready / error)

DocumentChunk   ← 文档分块（含嵌入向量）
  ├── document_id → ChatDocument
  ├── content
  ├── chunk_index
  └── embedding  (JSON 序列化的 float 数组)
```

### 4.4 前端架构

```
art-design-pro/src/
├── api/chat.ts                                    # API 调用 + SSE 流处理
└── components/core/layouts/art-chat-window/
    └── index.vue                                  # 主聊天窗口组件
```

## 5. 本地开源模型部署指南

### 5.1 使用 Ollama 部署

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 拉取模型
ollama pull qwen2.5:7b          # 通义千问 2.5 7B
ollama pull deepseek-r1:8b      # DeepSeek R1 8B
ollama pull llama3.1:8b         # Llama 3.1 8B

# 拉取 Embedding 模型 (RAG 用)
ollama pull nomic-embed-text

# 启动服务 (默认 127.0.0.1:11434)
ollama serve
```

平台配置：
```bash
export LLM_PROVIDER=ollama
export LLM_API_BASE_URL=http://127.0.0.1:11434/v1
export LLM_MODEL=qwen2.5:7b
export EMBEDDING_MODEL=nomic-embed-text
```

### 5.2 使用 vLLM 部署

```bash
pip install vllm

# 启动 OpenAI-compatible 服务
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 --port 8000
```

平台配置：
```bash
export LLM_PROVIDER=custom
export LLM_API_BASE_URL=http://127.0.0.1:8000/v1
export LLM_API_KEY=EMPTY
export LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

## 6. 多提供商完整配置示例

以下示例同时配置 OpenAI（默认） + DeepSeek + 本地 Ollama：

```bash
# 默认提供商 (OpenAI)
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-openai-key-xxx
export LLM_MODEL=gpt-4o-mini

# 额外提供商
export LLM_PROVIDERS_JSON='[
  {
    "name": "deepseek",
    "display_name": "DeepSeek",
    "api_key": "sk-deepseek-key-xxx",
    "models": ["deepseek-chat", "deepseek-reasoner"],
    "default_model": "deepseek-chat"
  },
  {
    "name": "ollama",
    "display_name": "本地 Ollama",
    "base_url": "http://127.0.0.1:11434/v1",
    "models": ["qwen2.5:7b", "deepseek-r1:8b"],
    "default_model": "qwen2.5:7b"
  }
]'

# Embedding (使用 OpenAI)
export EMBEDDING_MODEL=text-embedding-3-small

# RAG
export RAG_ENABLED=true
export RAG_CHUNK_SIZE=500
export RAG_TOP_K=3
```
