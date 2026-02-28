# 数据生成平台 API 与数据模型规范

> 本文档详细列出平台所有 API 端点与数据模型定义，作为前后端开发的权威契约。  
> 系统总览见 [系统概述](数据生成平台系统概述.md)，前端契约差异见 [前端契约与后端适配差异清单](前端契约与后端适配差异清单.md)。

---

## 1. 通用约定

### 1.1 请求协议

- 基础路径：`/api`
- 鉴权方式：`Authorization: Bearer <token>`（后端同时兼容 `Authorization: <token>`）
- Content-Type：`application/json`（文件上传除外）

### 1.2 响应格式

所有接口统一返回 HTTP 200，业务状态通过响应体 `code` 表达：

```json
{
  "code": 200,
  "msg": "success",
  "data": { ... }
}
```

- `code === 200` 表示成功
- `code !== 200` 表示业务错误，`msg` 字段包含错误描述

### 1.3 分页接口

分页接口的 `data` 字段结构（兼容前端 `useTable`）：

```json
{
  "records": [...],
  "current": 1,
  "size": 10,
  "total": 100
}
```

### 1.4 SSE 流式接口

Chat / Skills 接口返回 `text/event-stream`，事件格式：

```
data: {"type": "token", "content": "文本片段"}
data: {"type": "tool_call", "name": "...", "arguments": "..."}
data: {"type": "tool_result", "name": "...", "result": "..."}
data: {"type": "rag_citations", "citations": [...]}
data: {"type": "done", "content": ""}
data: {"type": "error", "content": "错误信息"}
```

---

## 2. API 端点详细说明

### 2.1 认证模块 (`/api/auth`)

| 方法 | 路径                 | 鉴权 | 说明     |
|------|---------------------|------|---------|
| POST | `/api/auth/login`   | 否   | 用户登录  |
| POST | `/api/auth/register`| 否   | 用户注册  |

#### POST /api/auth/login

```json
// 请求体
{ "userName": "admin", "password": "123456" }

// 成功响应
{
  "code": 200,
  "data": { "token": "eyJhbG...", "refreshToken": "..." }
}
```

#### POST /api/auth/register

```json
// 请求体
{ "username": "zhangsan", "email": "a@b.com", "password": "xxx" }

// 成功响应
{ "code": 200, "msg": "注册成功" }
```

---

### 2.2 用户模块 (`/api/user`)

| 方法 | 路径              | 鉴权 | 说明                                      |
|------|------------------|------|------------------------------------------|
| GET  | `/api/user/info` | 是   | 当前用户信息                                |
| GET  | `/api/user/list` | 是   | 用户列表（分页），参数：current, size, username |

#### GET /api/user/info 响应

```json
{
  "code": 200,
  "data": {
    "userId": 1,
    "userName": "admin",
    "email": "admin@example.com",
    "avatar": "",
    "roles": ["admin"],
    "buttons": ["add", "edit", "delete"]
  }
}
```

---

### 2.3 角色模块 (`/api/role`)

| 方法 | 路径              | 鉴权 | 说明                          |
|------|------------------|------|------------------------------|
| GET  | `/api/role/list` | 是   | 角色列表（分页），参数：current, size |

---

### 2.4 系统模块 (`/api/v3/system`)

| 方法 | 路径                    | 鉴权 | 说明                            |
|------|------------------------|------|---------------------------------|
| GET  | `/api/v3/system/menus` | 是   | 菜单列表（兼容 art-design-pro）    |

返回 `AppRouteRecord[]` 结构，包含 `meta.authList` 供前端 `v-auth/hasAuth` 使用。

---

### 2.5 项目模块 (`/api/projects`)

| 方法   | 路径                                | 鉴权 | 说明                     |
|--------|-------------------------------------|------|-------------------------|
| POST   | `/api/projects`                     | 是   | 新建项目                  |
| GET    | `/api/projects`                     | 是   | 项目列表（支持 name/code 筛选）|
| PUT    | `/api/projects/{id}`                | 是   | 更新项目（仅 owner）        |
| DELETE | `/api/projects/{id}`                | 是   | 删除项目（仅 owner）        |
| POST   | `/api/projects/{id}/open_comfy`     | 是   | 启动/打开 ComfyUI          |

#### POST /api/projects

```json
// 请求体
{
  "name": "项目A",
  "code": "PRJ-001",
  "note": "项目备注",
  "target_count": 1000
}

// 成功响应
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "项目A",
    "code": "PRJ-001",
    "note": "项目备注",
    "owner_user_id": 1,
    "owner_user_name": "admin",
    "target_count": 1000,
    "generated_count": 0,
    "create_time": "2026-02-27 10:00:00",
    "update_time": "2026-02-27 10:00:00"
  }
}
```

#### POST /api/projects/{id}/open_comfy

```json
// 成功响应
{ "code": 200, "data": { "comfy_url": "http://10.10.1.199:8200" } }

// 达到目标数量上限
{ "code": 200, "msg": "已达到目标生成数量上限，请修改目标数量后继续" }

// 非 owner
{ "code": 403, "msg": "无操作权限" }
```

---

### 2.6 生成日志模块 (`/api/logs`)

| 方法 | 路径          | 鉴权 | 说明                                              |
|------|--------------|------|--------------------------------------------------|
| POST | `/api/logs`  | 是   | 写入生成日志                                        |
| GET  | `/api/logs`  | 是   | 查询生成日志，参数：user_id, project_id, start, end  |

#### POST /api/logs

```json
// 请求体
{
  "project_id": 1,
  "status": "成功",
  "prompt_id": "abc123",
  "timestamp": "2026-02-27T10:15:00",
  "details": { "duration_ms": 5200 }
}
```

#### GET /api/logs 响应

```json
{
  "code": 200,
  "data": {
    "records": [
      {
        "id": 1,
        "user_name": "admin",
        "project_name": "项目A",
        "timestamp": "2026-02-27 10:15:00",
        "status": "成功",
        "prompt_id": "abc123"
      }
    ],
    "current": 1,
    "size": 20,
    "total": 1
  }
}
```

---

### 2.7 数据统计模块 (`/api/stats`, `/api/export`)

| 方法 | 路径            | 鉴权 | 说明                                              |
|------|----------------|------|--------------------------------------------------|
| GET  | `/api/stats`   | 是   | 统计聚合，参数：dimension(day/project/user), start_date, end_date |
| GET  | `/api/export`  | 是   | 导出统计 Excel，参数同上                              |

#### GET /api/stats 响应

```json
{
  "code": 200,
  "data": [
    { "key": "2026-02-25", "count": 50 },
    { "key": "2026-02-26", "count": 80 }
  ]
}
```

#### GET /api/export

返回 Excel 文件流（`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）。

---

### 2.8 服务器监控模块 (`/api/server`)

| 方法 | 路径                          | 鉴权 | 说明             |
|------|------------------------------|------|-----------------|
| GET  | `/api/server/stats`          | 是   | 实时资源监控      |
| GET  | `/api/server/stats/history`  | 是   | 历史监控数据      |

#### GET /api/server/stats 响应

```json
{
  "code": 200,
  "data": {
    "cpu": 23.5,
    "memory": 45.2,
    "memory_total_gb": 31.2,
    "memory_used_gb": 14.1,
    "swap": 12.3,
    "disk": 67.8,
    "disk_total_gb": 500.0,
    "disk_used_gb": 339.0
  }
}
```

---

### 2.9 AI 对话模块 (`/api/chat`)

#### 提供商 & 配置

| 方法 | 路径                    | 鉴权 | 说明                    |
|------|------------------------|------|------------------------|
| GET  | `/api/chat/providers`  | 是   | 获取可用 LLM 提供商列表  |

#### 会话管理

| 方法   | 路径                             | 鉴权 | 说明             |
|--------|----------------------------------|------|-----------------|
| POST   | `/api/chat/sessions`             | 是   | 新建对话会话      |
| GET    | `/api/chat/sessions`             | 是   | 获取会话列表      |
| GET    | `/api/chat/sessions/{id}`        | 是   | 获取会话详情      |
| PUT    | `/api/chat/sessions/{id}`        | 是   | 更新会话信息      |
| DELETE | `/api/chat/sessions/{id}`        | 是   | 删除会话         |

#### POST /api/chat/sessions

```json
// 请求体
{
  "title": "新对话",
  "model_provider": "openai",
  "model_name": "gpt-4o-mini",
  "system_prompt": ""
}
```

#### 消息 & 对话

| 方法 | 路径                                     | 鉴权 | 说明                     |
|------|------------------------------------------|------|-------------------------|
| GET  | `/api/chat/sessions/{id}/messages`       | 是   | 获取消息历史              |
| POST | `/api/chat/sessions/{id}/chat`           | 是   | 发送消息（SSE 流式响应）   |

#### POST /api/chat/sessions/{id}/chat

```json
// 请求体
{
  "content": "用户消息",
  "model_provider": "openai",
  "model_name": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 4096,
  "enable_rag": true,
  "enable_agent": false,
  "document_ids": [1, 2]
}
```

返回 SSE 流。启用 `enable_agent` 时走 Agent 工具调用流程。

#### 图片（多模态）

| 方法 | 路径                              | 鉴权 | 说明             |
|------|-----------------------------------|------|-----------------|
| POST | `/api/chat/images/upload`         | 是   | 上传图片          |
| GET  | `/api/chat/images/{filename}`     | 否   | 获取图片          |

#### 文档（RAG）

| 方法   | 路径                                  | 鉴权 | 说明             |
|--------|---------------------------------------|------|-----------------|
| POST   | `/api/chat/documents/upload`          | 是   | 上传文档          |
| GET    | `/api/chat/documents`                 | 是   | 获取文档列表      |
| DELETE | `/api/chat/documents/{id}`            | 是   | 删除文档          |
| GET    | `/api/chat/documents/{id}/preview`    | 是   | 预览文档内容      |

#### 用量 & 报告

| 方法 | 路径                              | 鉴权 | 说明                         |
|------|-----------------------------------|------|------------------------------|
| GET  | `/api/chat/usage`                 | 是   | 当前用户 Token 用量            |
| GET  | `/api/chat/usage/all`             | 是   | 所有用户 Token 用量（管理员）    |
| GET  | `/api/chat/reports/{filename}`    | 是   | 下载报告文件                   |

#### Skills 技能

| 方法 | 路径                              | 鉴权 | 说明                       |
|------|-----------------------------------|------|---------------------------|
| GET  | `/api/chat/skills`                | 是   | 获取可用技能列表              |
| POST | `/api/chat/skills/{id}/run`       | 是   | 执行技能（SSE 流式响应）      |

#### POST /api/chat/skills/{id}/run

```json
// 请求体
{
  "content": "用户输入内容",
  "model_provider": "openai",
  "model_name": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

返回 SSE 流（`token` → `done`）。

---

### 2.10 工作流模块 (`/api/workflow`)

| 方法 | 路径                         | 鉴权 | 说明                     |
|------|------------------------------|------|-------------------------|
| GET  | `/api/workflow/templates`    | 是   | 获取工作流模板列表         |
| POST | `/api/workflow/generate`     | 是   | AI 生成工作流             |
| POST | `/api/workflow/submit`       | 是   | 提交工作流到 ComfyUI      |
| PUT  | `/api/workflow/modify`       | 是   | AI 修改工作流参数          |

#### POST /api/workflow/generate

```json
// 请求体
{ "description": "生成一张赛博朋克风格的城市夜景，分辨率 1024x768" }

// 成功响应
{ "code": 200, "data": { "workflow": { ... }, "description": "..." } }
```

#### POST /api/workflow/submit

```json
// 请求体
{
  "workflow": { ... },
  "comfy_url": "http://127.0.0.1:8200"
}

// 成功响应
{ "code": 200, "data": { "prompt_id": "abc123" } }
```

#### PUT /api/workflow/modify

```json
// 请求体
{
  "workflow": { ... },
  "modification": "把分辨率改成 1024x1024，步数改为 30"
}

// 成功响应
{ "code": 200, "data": { "workflow": { ... }, "changes": "..." } }
```

---

## 3. 数据模型定义

### 3.1 User（框架内置）

| 字段           | 类型        | 说明                 |
|----------------|------------|---------------------|
| id             | BigInt     | 主键                 |
| username       | CharField  | 用户名               |
| email          | CharField  | 邮箱                 |
| password_hash  | CharField  | 密码哈希（Argon2）    |
| is_active      | Boolean    | 是否激活              |
| is_superuser   | Boolean    | 是否超级管理员         |
| created_at     | DateTime   | 创建时间              |
| updated_at     | DateTime   | 更新时间              |

### 3.2 Role（框架内置）

| 字段       | 类型        | 说明        |
|-----------|------------|------------|
| id        | BigInt     | 主键        |
| name      | CharField  | 角色名称    |
| desc      | CharField  | 角色描述    |

多对多关系：User ↔ Role ↔ Menu / API。

### 3.3 Project

| 字段           | 类型        | 说明                         |
|----------------|------------|------------------------------|
| id             | BigInt     | 主键                          |
| name           | CharField  | 项目名称                       |
| code           | CharField  | 项目号（唯一）                  |
| note           | TextField  | 备注                          |
| owner_user_id  | BigInt     | 创建者用户 ID                   |
| target_count   | Int        | 目标生成数量（0 = 不限制）       |
| generated_count| Int        | 已生成数量                      |
| created_at     | DateTime   | 创建时间                       |
| updated_at     | DateTime   | 更新时间                       |

### 3.4 ComfyUIService

| 字段           | 类型        | 说明                              |
|----------------|------------|----------------------------------|
| id             | BigInt     | 主键                              |
| user_id        | BigInt     | 用户 ID                           |
| project_id     | BigInt     | 项目 ID                           |
| port           | Int        | 端口号                            |
| status         | CharField  | 状态：`online` / `offline`         |
| comfy_url      | CharField  | 访问地址                           |
| pid            | Int        | 进程 PID                          |
| base_dir       | CharField  | 实例 base 目录                     |
| log_path       | CharField  | 实例日志路径                        |
| last_heartbeat | DateTime   | 最后心跳时间                        |
| start_time     | DateTime   | 启动时间                           |

唯一约束：`(user_id, project_id)`。

### 3.5 GenerationLog

| 字段          | 类型        | 说明                        |
|---------------|------------|-----------------------------|
| id            | BigInt     | 主键                         |
| user_id       | BigInt     | 用户 ID                      |
| project_id    | BigInt     | 项目 ID                      |
| timestamp     | DateTime   | 生成时间                      |
| status        | CharField  | 状态：成功 / 失败              |
| prompt_id     | CharField  | ComfyUI prompt_id            |
| concurrent_id | BigInt     | 并发 ID                      |
| details       | JSON       | 详情（错误信息/耗时等）         |

唯一约束：`(project_id, prompt_id)`。  
联合索引：`(project_id, timestamp)`、`(user_id, timestamp)`。

### 3.6 ChatSession

| 字段           | 类型        | 说明                   |
|----------------|------------|----------------------|
| id             | BigInt     | 主键                  |
| user_id        | BigInt     | 用户 ID                |
| title          | CharField  | 会话标题（默认"新对话"） |
| model_provider | CharField  | 模型提供商              |
| model_name     | CharField  | 模型名称               |
| system_prompt  | TextField  | 系统提示词              |
| is_deleted     | Boolean    | 软删除标识              |
| created_at     | DateTime   | 创建时间               |
| updated_at     | DateTime   | 更新时间               |

### 3.7 ChatMessage

| 字段        | 类型        | 说明                             |
|-------------|------------|----------------------------------|
| id          | BigInt     | 主键                              |
| session_id  | BigInt     | 关联 ChatSession                   |
| role        | CharField  | 角色：`user` / `assistant` / `system` |
| content     | TextField  | 消息内容                            |
| token_count | Int        | Token 数量                         |
| created_at  | DateTime   | 创建时间                            |

### 3.8 ChatDocument

| 字段        | 类型        | 说明                                    |
|-------------|------------|----------------------------------------|
| id          | BigInt     | 主键                                    |
| user_id     | BigInt     | 用户 ID                                 |
| filename    | CharField  | 原始文件名                               |
| file_path   | CharField  | 存储路径                                 |
| file_size   | Int        | 文件大小（字节）                           |
| file_type   | CharField  | 文件类型                                 |
| chunk_count | Int        | 分块数量                                 |
| status      | CharField  | 状态：`processing` / `ready` / `error`   |
| error_msg   | TextField  | 错误信息                                 |
| created_at  | DateTime   | 创建时间                                 |

### 3.9 DocumentChunk

| 字段         | 类型        | 说明                       |
|-------------|------------|---------------------------|
| id          | BigInt     | 主键                       |
| document_id | BigInt     | 关联 ChatDocument            |
| content     | TextField  | 分块文本内容                 |
| chunk_index | Int        | 分块索引                    |
| embedding   | TextField  | 嵌入向量（JSON 序列化 float[]）|
| created_at  | DateTime   | 创建时间                    |

### 3.10 TokenUsage

| 字段              | 类型        | 说明              |
|-------------------|------------|------------------|
| id                | BigInt     | 主键              |
| user_id           | BigInt     | 用户 ID            |
| provider          | CharField  | 模型提供商          |
| model             | CharField  | 模型名称           |
| prompt_tokens     | Int        | Prompt Token 数量  |
| completion_tokens | Int        | Completion Token 数 |
| created_at        | DateTime   | 记录时间           |

---

## 4. 前后端契约要点

1. **鉴权头**：前端注入 `Authorization`，后端兼容 `Bearer <token>` 与 `<token>` 两种格式
2. **响应码**：前端按 `code === 200` 判定成功，后端统一返回 HTTP 200 + 响应体 `code`
3. **分页结构**：`data: { records, current, size, total }`
4. **菜单权限**：后端返回 `AppRouteRecord[]`，`meta.authList[{title, authMark}]` 供前端按钮权限使用
5. **SSE 流式**：Nginx 需关闭 `proxy_buffering`，设置 `proxy_read_timeout 300s`

详见 [前端契约与后端适配差异清单](前端契约与后端适配差异清单.md)。

---

*文档版本：v3.0*  
*更新日期：2026-02-27*
