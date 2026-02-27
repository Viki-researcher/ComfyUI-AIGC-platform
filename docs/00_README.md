# 数据生成平台文档索引

> 本目录包含数据生成平台（AIGC Platform）的全部技术文档。
> 文档编号约定：`0x` = 环境部署，`1x` = 架构与运行，`2x` = API 与开发规范，`3x` = 功能模块。

## 快速导航

| 编号 | 文档 | 说明 |
|------|------|------|
| 00 | 本文件 | 文档索引 |
| 01 | [环境与依赖安装](01_环境与依赖安装.md) | Node.js、Python、conda、PostgreSQL 安装 |
| 02 | [PostgreSQL 安装与初始化](02_PostgreSQL_安装与初始化规范.md) | 数据库创建与配置 |
| 03 | [配置说明](03_配置说明_前端后端ComfyUI.md) | 环境变量、端口、数据库、ComfyUI、标注工具 |
| 04 | [SQLite 到 PostgreSQL 迁移](04_SQLite_to_PostgreSQL_迁移说明.md) | 数据库迁移方案与对比 |
| 10 | [平台启动与停止](10_平台启动与停止.md) | 一键脚本、手动启停 |
| 11 | [ComfyUI 启动逻辑](11_ComfyUI_启动逻辑说明.md) | 后端如何管理 ComfyUI 实例 |
| 20 | [系统架构与功能总览](20_系统架构与功能总览.md) | **权威功能说明**（合并原系统概述+功能模块文档） |
| 21 | [API 接口规范](21_API接口完整规范.md) | 全部 REST API 端点定义 |
| 22 | [前后端协同开发规范](数据生成平台前后端协同开发规范.md) | 鉴权、权限、表单、数据库设计规范 |
| 23 | [前端契约与后端适配](前端契约与后端适配差异清单.md) | 前后端接口差异对照 |
| 30 | [Docker Compose 部署](30_Docker_Compose部署.md) | 容器化一键部署指南 |

## 仓库目录结构

```
/workspace
├── art-design-pro/           # 前端（Vue3 + Vite + Element Plus）
├── vue-fastapi-admin-main/   # 后端（FastAPI + Tortoise ORM）
├── ComfyUI-master-fitow/     # ComfyUI 引擎（AI图像生成）
├── sam3-annotation-tool/     # SAM3 标注工具（数据标注）
├── docker-compose.yml        # 容器化部署配置
└── docs/                     # 本文档目录
```
