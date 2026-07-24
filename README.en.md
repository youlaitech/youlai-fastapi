<div align="center">



# <img alt="youlai-fastapi" width="28" src="./docs/images/logo/logo.png" align="center"> youlai-fastapi



**Enterprise-grade permission management backend based on FastAPI (Python)**



[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?logo=redis&logoColor=white)](https://redis.io/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue?logo=apache)](LICENSE)

[![Gitee Star](https://gitee.com/youlaiorg/youlai-fastapi/badge/star.svg)](https://gitee.com/youlaiorg/youlai-fastapi/stargazers)

[![GitHub Star](https://img.shields.io/github/stars/youlaitech/youlai-fastapi?style=social)](https://github.com/youlaitech/youlai-fastapi)



</div>



![](./docs/images/rainbow.png "rainbow.png")



<div align="center">



[![Live Preview](https://img.shields.io/badge/Live%20Preview-2D8CF0?style=for-the-badge&logo=google-chrome&logoColor=white)](https://vue.youlai.tech)

[![Mobile Preview](https://img.shields.io/badge/Mobile%20Preview-19BE6B?style=for-the-badge&logo=android&logoColor=white)](https://app.youlai.tech)

[![Documentation](https://img.shields.io/badge/Documentation-8B5CF6?style=for-the-badge&logo=gitbook&logoColor=white)](https://www.youlai.tech/docs/server/spring-boot/)

[![简体中文](https://img.shields.io/badge/简体中文-00B4D8?style=for-the-badge&logo=google-translate&logoColor=white)](./README.md)



</div>



## Introduction



**youlai-fastapi** is an enterprise-grade permission management backend built on Python (FastAPI + SQLAlchemy + PostgreSQL), with the frontend [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) and the mobile app [youlai-app](https://gitee.com/youlaiorg/youlai-app). It is one of the official **7 language implementations** (Java / Node.js / Go / Python / PHP / C# / Rust), sharing the same **RESTful API specification** and **database schema**, so the frontend can switch seamlessly. It is ideal for teams on the Python stack who want to learn or build on an enterprise admin system.



## Core Features



- 🔐 **Security** — PyJWT + bcrypt + Redis Token, with token issuance, renewal, and multi-device sessions

- 🛡️ **Fine-grained permissions** — RBAC at data / menu / button / API level, with five data-scope tiers

- ⚡ **Code generator** — one-click generation of full-stack CRUD code

- 📦 **Complete modules** — users, roles, menus, departments, dictionaries, configs, files, notices, operation logs

- 🌐 **Multi-language ecosystem** — shares the API spec and database schema with other language versions

- 🔌 **Real-time communication** — SSE push: online user count, dictionary sync, notification broadcast



## System Preview



**PC**



<table align="center">

  <tr>

    <td><img alt="PC Preview 1" width="400" src="./docs/images/preview/pc-01.png"></td>

    <td><img alt="PC Preview 2" width="400" src="./docs/images/preview/pc-02.png"></td>

  </tr>

  <tr>

    <td><img alt="PC Preview 3" width="400" src="./docs/images/preview/pc-03.png"></td>

    <td><img alt="PC Preview 4" width="400" src="./docs/images/preview/pc-04.png"></td>

  </tr>

  <tr>

    <td><img alt="PC Preview 5" width="400" src="./docs/images/preview/pc-05.png"></td>

    <td><img alt="PC Preview 6" width="400" src="./docs/images/preview/pc-06.png"></td>

  </tr>

</table>



**Mobile**



<table align="center">

  <tr>

    <td><img alt="App Preview 1" width="200" src="./docs/images/preview/app-01.png"></td>

    <td><img alt="App Preview 2" width="200" src="./docs/images/preview/app-02.png"></td>

    <td><img alt="App Preview 3" width="200" src="./docs/images/preview/app-03.png"></td>

    <td><img alt="App Preview 4" width="200" src="./docs/images/preview/app-04.png"></td>

  </tr>

</table>



## Quick Start



**Requirements**: Python 3.11+ · PostgreSQL 16+ · Redis 7.x



1. Clone: `git clone https://github.com/youlaitech/youlai-fastapi.git`

2. Create a virtual environment and install dependencies:

   ```bash

   python -m venv .venv

   .venv\Scripts\activate   # Windows

   # source .venv/bin/activate  # Linux/Mac

   pip install fastapi[standard] uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic[email] pydantic-settings pyjwt[crypto] bcrypt python-multipart redis[hiredis] orjson loguru fastapi-pagination sse-starlette pillow openpyxl minio slowapi

   ```

3. Configure environment: `cp .env.example .env` (edit the DB connection in `.env`)

4. Create and initialize the database:

   ```bash

   createdb youlai_admin

   psql -d youlai_admin -f sql/postgresql/youlai-admin.sql

   ```

5. Start and visit http://localhost:8000/docs



Default credentials: `admin` / `123456`



**Docker**: `docker compose up -d`



## Tech Stack



| Tech | Version | Description |

|:-----|:--------|:------------|

| FastAPI | 0.115+ | Web framework |

| Uvicorn | 0.30+ | ASGI server |

| SQLAlchemy | 2.0 async | ORM (asyncpg driver) |

| Pydantic | v2 | Data validation |

| PostgreSQL | 16+ | Primary database |

| Redis | 7.x | Cache / Session |

| PyJWT | — | Auth token |

| bcrypt | — | Password hashing |

| loguru | — | Logging |

| MinIO | — | Object storage |

| slowapi | — | Rate limiting |



## Directory Structure



> Follows [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices): organized by business domain, each module self-contains `router/schemas/models/service`.



```

youlai-fastapi/

├── app/

│   ├── main.py              # FastAPI entry

│   ├── config.py            # Pydantic Settings

│   ├── database.py          # async engine + session

│   ├── redis.py             # Redis connection pool

│   ├── response.py          # Result + ResultCode unified response

│   ├── exceptions.py        # BusinessException + global handlers

│   ├── pagination.py        # PageQuery / PageResult

│   ├── constants.py         # global constants

│   ├── dependencies.py      # get_current_user / require_perm

│   ├── middleware.py        # CORS / logging / rate limit

│   ├── models/              # ORM base + domain model registry

│   ├── auth/                # auth (login/logout/refresh/captcha)

│   ├── user/  role/  menu/  dept/  dict/  sysconfig/  notice/  log/

│   ├── captcha/             # image captcha

│   ├── file/                # file service (MinIO/local)

│   ├── codegen/             # code generator

│   ├── wxma/                # WeChat Mini Program

│   └── sse/                 # SSE push

├── alembic/                 # database migration

├── tests/                   # tests

├── sql/postgresql/          # database init scripts

├── docs/images/             # README image assets

├── Dockerfile               # container build

├── docker-compose.yml       # container orchestration

├── pyproject.toml           # dependency management

└── README.md

```



## Ecosystem



**Frontend**



| Project | Stack | Description |

|:-----|:------|:------------|

| [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) | Vue 3 + Element Plus | PC admin frontend (recommended) |

| [youlai-app](https://gitee.com/youlaiorg/youlai-app) | Vue 3 + UniApp | Mobile App |



**Backend**



| Project | Stack | Description |
| [youlai-boot](https://gitee.com/youlaiorg/youlai-boot) | Spring Boot + MyBatis-Plus | Java (recommended) |
| [youlai-nest](https://gitee.com/youlaiorg/youlai-nest) | NestJS + TypeORM | Node.js |
| [youlai-gin](https://gitee.com/youlaiorg/youlai-gin) | Go + Gorm | Go |
| [youlai-django](https://gitee.com/youlaiorg/youlai-django) | Django + DRF | Python |
| [youlai-fastapi](https://gitee.com/youlaiorg/youlai-fastapi) | FastAPI + SQLAlchemy | Python |
| [youlai-think](https://gitee.com/youlaiorg/youlai-think) | ThinkPHP + ThinkORM | PHP |
| [youlai-aspnet](https://gitee.com/youlaiorg/youlai-aspnet) | ASP.NET Core + EF Core | C# |
| [youlai-axum](https://gitee.com/youlaiorg/youlai-axum) | Axum + SeaORM | Rust |
> **youlai-boot** also provides the following variants and branches: [Multi-Tenant](https://gitee.com/youlaiorg/youlai-boot-tenant) · [MyBatis-Flex](https://gitee.com/youlaiorg/youlai-boot-flex) · [Spring Boot 3](https://gitee.com/youlaiorg/youlai-boot/tree/spring-boot-3) · [PostgreSQL](https://gitee.com/youlaiorg/youlai-boot/tree/db-pg) · [Multi-Module](https://gitee.com/youlaiorg/youlai-boot/tree/multi-module)

>

> The eight backends share the same **RESTful API specification** and **database schema**, so the frontend can switch seamlessly.



## Documentation



| Resource | Link |

|:-----|:-----|

| 📖 Full docs site | [www.youlai.tech](https://www.youlai.tech/) |

| 🖥️ PC live preview | [vue.youlai.tech](https://vue.youlai.tech) |

| 📱 Mobile live preview | [app.youlai.tech](https://app.youlai.tech) |

| 🔗 Apifox API docs | [apifox.com](https://www.apifox.cn/apidoc/shared-195e783f-4d85-4235-a038-eec696de4ea5) |

| 🔗 Local API docs | [localhost:8000/docs](http://localhost:8000/docs) |



## Contributing



Issues and Pull Requests are welcome! See the [Contribution Guide](https://www.youlai.tech/faq/help).



## License



Released under the [Apache License 2.0](LICENSE); free for commercial use.



---



<table align="center">

  <tr>

    <td align="center">

      <img src="./docs/images/qrcode/wechat-official.jpg" height="180" alt="Official WeChat Account"><br>

      <sub>Official WeChat Account</sub>

    </td>

    <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>

    <td align="center">

      <img src="./docs/images/qrcode/wechat-mp.jpg" height="180" alt="Mini Program"><br>

      <sub>Mini Program</sub>

    </td>

    <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>

    <td align="center">

      <img src="./docs/images/qrcode/wechat-personal.png" height="180" alt="Add author on WeChat"><br>

      <sub>Add author on WeChat</sub>

    </td>

  </tr>

</table>



<p align="center"><em>Technical discussion · Feedback · Business cooperation</em></p>

