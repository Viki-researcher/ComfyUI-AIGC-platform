# 数据生成平台文档索引

> 本目录包含数据生成平台（AIGC Platform）的全部技术文档。
> 文档编号约定：`0x` = 环境部署，`1x` = 架构与运行，`2x` = API 与开发规范，`3x` = 部署与配置。

## 快速导航

| 编号 | 文档 | 说明 |
|------|------|------|
| 00 | 本文件 | 文档索引 |
| 01 | [环境与依赖安装](01_环境与依赖安装.md) | Node.js、Python、conda、PostgreSQL |
| 02 | [PostgreSQL 安装与初始化](02_PostgreSQL_安装与初始化规范.md) | 数据库创建与配置 |
| 03 | [配置说明](03_配置说明_前端后端ComfyUI.md) | 环境变量、ComfyUI、标注工具、LLM/RAG |
| 04 | [SQLite 到 PostgreSQL 迁移](04_SQLite_to_PostgreSQL_迁移说明.md) | 数据库迁移方案 |
| 10 | [平台启动与停止](10_平台启动与停止.md) | 一键脚本、手动启停 |
| 11 | [ComfyUI 启动逻辑](11_ComfyUI_启动逻辑说明.md) | 后端如何管理 ComfyUI |
| 20 | [**系统架构与功能总览**](20_系统架构与功能总览.md) | 📌 权威功能说明（全部模块） |
| 21 | [API 接口完整规范](21_API接口完整规范.md) | 全部 REST API 端点定义 |
| 22 | [前后端协同开发规范](数据生成平台前后端协同开发规范.md) | 鉴权、权限、数据库规范 |
| 23 | [前端契约与后端适配](前端契约与后端适配差异清单.md) | 接口差异对照 |
| 30 | [Docker Compose 部署](30_Docker_Compose部署.md) | 容器化一键部署 |
| — | [LLM/AI Chat 配置](llm-chat-config.md) | 大模型对话系统配置 |
| — | [Skills 技能系统](skills-config.md) | 技能定义与配置 |
| — | [部署指南](deployment-guide.md) | 完整部署流程 |

## 功能模块总览

| 模块 | 说明 | 页面路由 |
|------|------|----------|
| 🏠 仪表盘 | 全局概览（今日生成量/项目数/成功率） | `/platform/dashboard` |
| 📋 个人工作台 | 项目卡片（进度条/状态灯/目标上限） | `/platform/workbench` |
| ✨ Prompt 助手 | 风格模板 Prompt 生成 | `/platform/prompt` |
| 📊 数据统计 | 趋势图 + 多维度筛选 | `/platform/stats` |
| 📝 生成日志 | 筛选 + Excel 导出 | `/platform/logs` |
| 🖥️ 服务器监控 | CPU/内存/GPU 指标 | `/platform/monitor` |
| 🔧 工作流编辑器 | ComfyUI 工作流管理 | `/platform/workflow` |
| 💰 用量与计费 | AI 调用量统计 | `/platform/usage` |
| 🤖 AI 对话 | LLM/Agent/RAG 聊天 | 全局聊天窗口 |
| 🏷️ 数据标注 | SAM3 标注（YOLO/COCO） | 项目卡片启动 |
| 📦 数据集导出 | YOLO/COCO 格式下载 | API 端点 |

## 仓库目录结构

```
/workspace
├── art-design-pro/           # 前端（Vue3 + Vite + Element Plus）
├── vue-fastapi-admin-main/   # 后端（FastAPI + Tortoise ORM）
├── ComfyUI-master-fitow/     # ComfyUI 引擎（AI图像生成）
├── sam3-annotation-tool/     # SAM3 标注工具（数据标注）
├── docker-compose.yml        # 容器化部署配置
├── .env.example              # 环境变量模板
└── docs/                     # 本文档目录
```
