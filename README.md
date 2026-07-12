<div align="center">

# <img alt="youlai-fastapi" width="28" src="./docs/images/logo/logo.png" align="center"> youlai-fastapi

[English](./README.en.md) · [简体中文](./README.md)

**FastAPI 企业级权限管理系统后端（Python）**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?logo=apache)](LICENSE)
[![Gitee Star](https://gitee.com/youlaiorg/youlai-fastapi/badge/star.svg)](https://gitee.com/youlaiorg/youlai-fastapi/stargazers)
[![GitHub Star](https://img.shields.io/github/stars/youlaitech/youlai-fastapi?style=social)](https://github.com/youlaitech/youlai-fastapi)

</div>

![](https://foruda.gitee.com/images/1708618984641188532/a7cca095_716974.png "rainbow.png")

<div align="center">

[🖥️ 在线预览](https://vue.youlai.tech) | [📲 移动端预览](https://app.youlai.tech) | [📖 文档](https://www.youlai.tech/docs/server/spring-boot/)

</div>

## 简介

**youlai-fastapi** 是一套基于 Python（FastAPI + SQLAlchemy 2.0 + PostgreSQL）的企业级权限管理系统后端，配套前端 [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) 和移动端 [youlai-app](https://gitee.com/youlaiorg/youlai-app)，并提供 **7 种语言实现**（Java / Node.js / Go / Python / PHP / C# / Rust），共享同一套 API 规范与数据库结构。适用于 Python 技术栈团队的企业中后台学习与二次开发。

## 核心特性

- 🔐 **安全体系** — PyJWT + bcrypt + Redis Token，支持令牌签发、续期与多端会话
- 🛡️ **细粒度权限** — RBAC 数据 / 菜单 / 按钮 / 接口级，数据权限五档
- ⚡ **代码生成器** — 一键生成前后端 CRUD 代码（codegen 模块）
- 📦 **模块齐全** — 用户、角色、菜单、部门、字典、配置、文件、通知、操作日志
- 🌐 **多语言生态** — 与其它语言版本共享 API 规范与数据库结构
- 🔌 **实时通信** — SSE 推送：在线用户数、字典同步、通知广播

## 系统预览

**PC 端**

<table align="center">
  <tr>
    <td><img alt="PC预览1" width="400" src="./docs/images/preview/pc-01.png"></td>
    <td><img alt="PC预览2" width="400" src="./docs/images/preview/pc-02.png"></td>
  </tr>
  <tr>
    <td><img alt="PC预览3" width="400" src="./docs/images/preview/pc-03.png"></td>
    <td><img alt="PC预览4" width="400" src="./docs/images/preview/pc-04.png"></td>
  </tr>
  <tr>
    <td><img alt="PC预览5" width="400" src="./docs/images/preview/pc-05.png"></td>
    <td><img alt="PC预览6" width="400" src="./docs/images/preview/pc-06.png"></td>
  </tr>
</table>

**移动端**

<table align="center">
  <tr>
    <td><img alt="APP预览1" width="200" src="./docs/images/preview/app-01.png"></td>
    <td><img alt="APP预览2" width="200" src="./docs/images/preview/app-02.png"></td>
    <td><img alt="APP预览3" width="200" src="./docs/images/preview/app-03.png"></td>
    <td><img alt="APP预览4" width="200" src="./docs/images/preview/app-04.png"></td>
  </tr>
</table>

## 快速开始

**环境要求**：Python 3.11+ · PostgreSQL 16+ · Redis 7.x

1. 克隆项目：`git clone https://github.com/youlaitech/youlai-fastapi.git`
2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install fastapi[standard] uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic[email] pydantic-settings pyjwt[crypto] bcrypt python-multipart redis[hiredis] orjson loguru fastapi-pagination sse-starlette pillow openpyxl minio slowapi
   ```
3. 配置环境变量：`cp .env.example .env`（按需修改 `.env` 中的数据库连接）
4. 创建并初始化数据库：
   ```bash
   createdb youlai_admin
   psql -d youlai_admin -f sql/postgresql/youlai-admin.sql
   ```
5. 启动服务：`fastapi dev app/main.py --host 0.0.0.0 --port 8000`，访问 http://localhost:8000/docs

默认账号：`admin` / `123456`

**Docker 部署**：`docker-compose -f docker/docker-compose.yml up -d`

## 技术栈

| 技术 | 版本 | 说明 |
|:-----|:-----|:-----|
| FastAPI | 0.115+ | Web 框架 |
| Uvicorn | 0.30+ | ASGI 服务器 |
| SQLAlchemy | 2.0 async | ORM（asyncpg 驱动） |
| Pydantic | v2 | 数据校验 |
| PostgreSQL | 16+ | 主数据库 |
| Redis | 7.x | 缓存 / 会话 |
| PyJWT | — | 认证令牌 |
| bcrypt | — | 密码加密 |
| loguru | — | 日志 |
| MinIO | — | 对象存储 |
| slowapi | — | 接口限流 |

## 目录结构

```
youlai-fastapi/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── core/                # 配置、数据库、Redis、安全
│   ├── common/              # 常量、枚举、分页
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── framework/           # 框架层
│   │   ├── security/        # JWT / 数据权限 / 验证码
│   │   ├── web/             # 统一响应 / 异常 / 限流
│   │   ├── middleware/      # 跨域 / 日志 / 限流
│   │   └── sse/             # SSE 消息推送
│   └── modules/             # 业务模块
│       ├── auth/            # 认证（登录/登出/刷新/验证码）
│       ├── system/          # 用户/角色/菜单/部门/字典/配置/通知/日志
│       ├── file/            # 文件服务（MinIO/本地）
│       └── codegen/         # 代码生成器
├── sql/postgresql/          # 数据库初始化脚本
├── docker/                  # Docker 部署编排
├── alembic/                 # 数据库迁移
├── pyproject.toml           # 依赖管理
└── README.md
```

## 生态矩阵

**前端**

| 项目 | 技术栈 | 说明 |
|:-----|:-------|:-----|
| [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) | Vue 3 + Element Plus | PC 管理前端（主推） |
| [youlai-app](https://gitee.com/youlaiorg/youlai-app) | Vue 3 + UniApp | 移动端 App |

**后端**

| 项目 | 技术栈 | 说明 |
|:-----|:-------|:-----|
| [youlai-boot](https://gitee.com/youlaiorg/youlai-boot) | Spring Boot 4 + MyBatis-Plus | Java（主推） |
| [youlai-nest](https://gitee.com/youlaiorg/youlai-nest) | NestJS + TypeORM | Node.js |
| [youlai-gin](https://gitee.com/youlaiorg/youlai-gin) | Go + Gorm | Go |
| [youlai-django](https://gitee.com/youlaiorg/youlai-django) | Django + DRF | Python |
| [youlai-thinkphp](https://gitee.com/youlaiorg/youlai-thinkphp) | ThinkPHP 8 | PHP |
| [youlai-aspnet](https://gitee.com/youlaiorg/youlai-aspnet) | ASP.NET Core | C# |
| [youlai-rust](https://gitee.com/youlaiorg/youlai-rust) | Axum + SeaORM | Rust |

> **youlai-boot** 还提供以下变种和分支版本：[多租户](https://gitee.com/youlaiorg/youlai-boot-tenant)（Spring Boot 4）· [MyBatis-Flex](https://gitee.com/youlaiorg/youlai-boot-flex)（Spring Boot 4）· [Spring Boot 3](https://gitee.com/youlaiorg/youlai-boot/tree/spring-boot-3) · [PostgreSQL](https://gitee.com/youlaiorg/youlai-boot/tree/db-pg) · [多模块](https://gitee.com/youlaiorg/youlai-boot/tree/multi-module)
>
> 七种后端共享同一套 **RESTful API 规范** 和 **数据库结构**，前端可无缝切换。

## 文档资源

| 资源 | 地址 |
|:-----|:-----|
| 📖 完整文档站 | [www.youlai.tech](https://www.youlai.tech/) |
| 🖥️ PC 端在线预览 | [vue.youlai.tech](https://vue.youlai.tech) |
| 📱 移动端在线预览 | [app.youlai.tech](https://app.youlai.tech) |
| 🔗 Apifox 接口文档 | [apifox.com](https://www.apifox.cn/apidoc/shared-195e783f-4d85-4235-a038-eec696de4ea5) |
| 🔗 本地接口文档 | [localhost:8000/docs](http://localhost:8000/docs) |

## 参与贡献

欢迎提交 Issue 和 Pull Request！详见 [贡献指南](https://www.youlai.tech/faq/help)。

## 开源协议

本项目基于 [Apache License 2.0](LICENSE) 开源，可免费用于商业项目。

---

<table align="center">
  <tr>
    <td align="center">
      <img src="./docs/images/qrcode/wechat-official.png" height="180" alt="公众号「有来技术」"><br>
      <sub>公众号「有来技术」</sub>
    </td>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
    <td align="center">
      <img src="./docs/images/qrcode/wechat-mp.jpg" height="180" alt="小程序「有来技术」"><br>
      <sub>小程序「有来技术」</sub>
    </td>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
    <td align="center">
      <img src="./docs/images/qrcode/wechat-personal.png" height="180" alt="添加作者微信"><br>
      <sub>添加作者微信</sub>
    </td>
  </tr>
</table>

<p align="center"><em>技术交流 · 问题反馈 · 商务合作</em></p>
