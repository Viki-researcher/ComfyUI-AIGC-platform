# 数据生成平台 — API 接口完整规范

> 本文档列出平台**全部** REST API 端点，包含请求参数和响应结构。
> 后端基础路径：`http://127.0.0.1:9999`，前端通过 Vite 代理 `/api` 转发。

## 通用约定

- **鉴权**：除登录/注册外，所有接口需 `Authorization: Bearer <token>` 头
- **响应格式**：`{ "code": 200, "msg": "OK", "data": ... }`，code=200 表示成功
- **分页**：`current`（页码，从1开始）、`size`（每页条数）、返回 `total`
- **日期格式**：`YYYY-MM-DD` 或 `YYYY-MM-DD HH:mm:ss`

---

## 1. 认证模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/register` | 注册 |
| GET | `/api/user/info` | 获取当前用户信息 |

### POST /api/auth/login

```json
// 请求
{ "userName": "admin", "password": "123456" }
// 响应
{ "code": 200, "data": { "token": "eyJ...", "refreshToken": "" } }
```

### POST /api/auth/register

```json
// 请求
{ "username": "zhangsan", "email": "a@b.com", "password": "123456" }
```

---

## 2. 仪表盘模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard` | 全局概览 |

### GET /api/dashboard

```json
{
  "today_count": 156,
  "yesterday_count": 203,
  "total_count": 1973,
  "success_count": 1580,
  "success_rate": 80.1,
  "active_projects": 5,
  "total_users": 4,
  "online_comfy": 1,
  "online_annotation": 0
}
```

---

## 3. 项目模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects` | 项目列表 |
| PUT | `/api/projects/{id}` | 更新项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/open_comfy` | 启动 ComfyUI |
| POST | `/api/projects/{id}/open_annotation` | 启动标注工具 |

### POST /api/projects

```json
// 请求
{ "name": "项目A", "code": "PRJ-001", "note": "备注", "target_count": 5000 }
// 响应 data
{
  "id": 1, "name": "项目A", "code": "PRJ-001", "note": "备注",
  "owner_user_id": 1, "owner_user_name": "admin",
  "target_count": 5000, "generated_count": 0,
  "comfy_status": "stopped", "annotation_status": "stopped",
  "create_time": "2026-02-27 10:00:00"
}
```

### POST /api/projects/{id}/open_comfy

成功：`{ "comfy_url": "http://127.0.0.1:8200" }`
目标已达：`{ "code": 400, "msg": "已达到目标生成数量上限（5000/5000）..." }`

### POST /api/projects/{id}/open_annotation

成功：`{ "annotation_url": "http://127.0.0.1:7860" }`

---

## 4. Prompt 助手模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/prompt/generate` | 生成 Prompt |
| GET | `/api/prompt/styles` | 风格模板列表 |

### POST /api/prompt/generate

```json
// 请求
{ "description": "一只猫坐在窗台上", "style": "写实摄影", "enhance": true }
// 响应 data
{
  "positive": "一只猫坐在窗台上, professional photography, ultra realistic, ...",
  "negative": "low quality, worst quality, blurry, ...",
  "style_used": "写实摄影",
  "tips": ["已启用写实摄影风格模板", "建议配合ControlNet使用"]
}
```

---

## 5. 统计模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 聚合统计 |
| GET | `/api/stats/trend` | 时序趋势 |
| GET | `/api/export` | 统计 Excel 导出 |

### GET /api/stats

参数：`dimension` (day/project/user)、`start_date`、`end_date`、`project_id`、`user_id`、`status`

### GET /api/stats/trend

参数：`group_by` (project/user)、`start_date`、`end_date`

```json
{ "dates": ["2026-02-20", "2026-02-21", ...], "series": [{ "name": "项目Alpha", "data": [15, 20, ...] }] }
```

---

## 6. 日志模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/logs` | 写入生成日志 |
| GET | `/api/logs` | 查询日志（分页） |
| GET | `/api/logs/export` | 导出日志 Excel |

### GET /api/logs

参数：`user_id`、`project_id`、`status`、`start`、`end`、`current`、`size`

---

## 7. 数据集模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dataset/export` | 导出数据集（YOLO/COCO） |

参数：`project_id`（必须）、`format`（yolo/coco）

响应：`application/zip` 二进制流。

---

## 8. 服务器监控模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/server/stats` | 系统指标 |

```json
{ "cpu": 23.5, "memory": 45.2, "swap": 12.3, "disk": 67.8, "gpu": { "available": false, "gpus": [] } }
```

---

## 9. 系统管理模块（框架内置）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v3/system/menus` | 动态菜单（前端路由） |
| GET | `/api/user/list` | 用户列表（分页） |
| GET | `/api/role/list` | 角色列表（分页） |

---

## 10. 内部回调

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/internal/comfy/callback` | ComfyUI 生成回调（需 `X-Platform-Secret` 头） |
