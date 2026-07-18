# youlai-fastapi 结构与代码评审及优化方案

## 1. 评审说明

- 评审日期：2026-07-16
- 评审对象：`youlai-fastapi`
- 社区基准：[`zhanymkanov/fastapi-best-practices`](https://github.com/zhanymkanov/fastapi-best-practices)，评审时 HEAD 为 `5e00aa6095521f0d00e4eec2ef0afa44cd566af4`
- 项目规范：`youlai-skills/skills/fastapi/SKILL.md`
- 评审范围：目录结构、模块边界、FastAPI/Pydantic、SQLAlchemy async、认证授权、数据权限、测试、依赖、Alembic、Docker、可观测性和项目文档

本次审计得到的工程基线：

| 指标 | 当前值 |
|---|---:|
| `app` Python 文件 | 75 |
| `app` 代码行数 | 约 4387 |
| 路由声明 | 99 |
| OpenAPI path | 80 |
| 测试 Python 文件 | 4 |
| 测试函数 | 10 |
| Alembic revision | 0 |
| `uv.lock` | 缺失 |
| CI / pre-commit | 缺失 |
| LICENSE | 缺失 |

验证边界：当前虚拟环境未安装 `pytest`、`ruff`、`mypy`、`alembic` 等开发依赖，因此无法执行完整测试和质量检查。本次使用现有运行依赖完成了应用导入、OpenAPI、ASGI 路由、CORS、Pydantic 转换和 Token 行为的定向复现；包含 Alembic 在内的 80 个 Python 文件通过 AST 语法解析。未连接项目配置中的外部数据库和 Redis。

## 2. 结论与评分

### 2.1 综合结论

项目的目录结构已经基本完成从“按技术层分包”到“按业务域组织”的转换，这是当前最成熟的部分。`app/system/*`、`app/tool/*`、根级基础设施和显式路由/模型注册都符合社区标杆的核心方向。

当前主要问题不是继续大规模搬目录，而是补齐重构后的正确性、安全和工程闭环。现状适合继续开发和演示，但在 P0 问题关闭前不应部署到生产环境。

### 2.2 评分

| 维度 | 权重 | 得分 | 评价 |
|---|---:|---:|---|
| 目录结构与模块边界 | 30% | 84/100 | 业务域组织清晰，少数大文件和跨域副作用仍需收敛 |
| 代码正确性与安全 | 45% | 49/100 | async 基础较好，但存在认证绕过、Token 生命周期、数据权限和 Schema 映射缺陷 |
| 工程化与上线准备 | 25% | 35/100 | 缺少锁文件、可执行测试、CI、迁移历史和可用容器启动链 |
| **综合评分** | **100%** | **56/100** | **结构基础可用，生产闭环不足** |

综合分计算：`84 * 30% + 49 * 45% + 35 * 25% = 56.0`。

### 2.3 修复后的预期

- 完成 P0：可达到约 65 分，消除直接发布风险。
- 完成 P0 + P1：可达到 75-80 分，具备稳定联调和预发布条件。
- 完成 P0 + P1 + 主要 P2：可达到 85 分以上，形成可持续维护的企业项目基线。

## 3. 与社区标杆的逐项对照

| 标杆实践 | 当前状态 | 结论 | 主要证据 |
|---|---|---|---|
| 按业务域组织代码 | `system/user|role|menu|dept|dict` 等域自包含 | 符合 | `app/system/*` |
| 根级基础设施保持简单 | config/database/redis/response 等平铺 | 符合 | `app/*.py` |
| 域间显式导入 | 使用完整模块路径，没有魔法扫描 | 符合 | `app/main.py:81`、`app/registry.py:7` |
| async 路由和 async DB | 主要 I/O 使用 `await` 和 `AsyncSession` | 基本符合 | `app/database.py:47`、各 service |
| 同步 SDK 放线程池 | MinIO、OpenPyXL、Pillow 已做线程池隔离 | 基本符合 | `app/tool/file/router.py:89`、`app/system/user/router.py:168`、`app/captcha/service.py:75` |
| 充分使用 Pydantic | Schema 较多，但约束和 ORM 别名不完整 | 部分符合 | 多个 Schema 使用 camelCase，却直接读取 snake_case ORM |
| 可控的全局 BaseModel | 缺失 | 不符合 | 没有统一 alias、时间序列化和响应模型基类 |
| 分域配置 | 所有配置集中在单一 `Settings` | 不符合 | `app/config.py:16` 至 `:61` |
| 依赖链复用 | 已有 `get_current_user`、`require_perm` | 部分符合 | 缺少资源级 dependency，部分路由未鉴权 |
| REST 与明确响应模型 | 路径基本统一，但所有接口缺少 `response_model` | 不符合 | OpenAPI 成功响应 schema 为 `{}` |
| 生产环境关闭文档 | Swagger/Redoc 永久开启 | 不符合 | `app/main.py:44` 至 `:46` |
| DB 约束命名约定 | `Base.metadata` 未设置 naming convention | 不符合 | `app/database.py:15` |
| 静态、可逆 Alembic 迁移 | `versions/` 为空 | 不符合 | `alembic/versions/` |
| 从第一天使用 async 测试客户端 | 使用 `httpx.ASGITransport` | 形式符合 | `tests/conftest.py:20` |
| 测试隔离外部依赖 | 测试直接依赖 Redis，且路径已漂移 | 不符合 | `tests/auth/test_auth.py` |
| Ruff 作为质量门禁 | pyproject 已配置，但本地和 CI 均未执行 | 部分符合 | `pyproject.toml:71`，无 CI |

## 4. 当前做得好的部分

1. **业务域结构已成型**
   - `user`、`role`、`menu`、`dept`、`dict` 基本具备 `models.py`、`schemas.py`、`service.py`、`router.py`。
   - 没有继续引入 `core/common/framework/modules` 等含义模糊的横向大包。

2. **基础设施职责较清楚**
   - 数据库会话、Redis、异常、统一响应、分页和中间件都有明确入口。
   - `app/registry.py` 集中注册 ORM 模型，服务应用启动和 Alembic metadata 收集。

3. **异步技术栈选择正确**
   - SQLAlchemy 2.0 async、asyncpg、redis.asyncio 的方向正确。
   - 同步 MinIO、Excel 和图片生成已主动移出事件循环。

4. **异常与业务码已有统一基础**
   - `BusinessException`、`ResultCode`、HTTP 状态码映射已经存在。
   - 全局异常处理会隐藏内部错误信息并记录 traceback。

5. **部分查询考虑了性能**
   - 用户列表使用批量查询部门和角色，避免逐用户 N+1。
   - SSE 使用 Redis Pub/Sub 和在线集合，考虑了多 worker 场景。

这些基础应保留，不建议为追求“更像模板”而做大规模重命名或重新分层。

## 5. P0：发布阻断问题

### P0-01：仓库已跟踪真实形态的密钥和连接凭据

证据：

- `.env` 当前被 Git 跟踪，并从初始化提交起存在。
- `app/config.py:17` 至 `:24` 内置远程数据库、Redis 和固定 JWT 密钥。
- `.env.example:2` 至 `:9`、`docker-compose.yml:9` 至 `:19` 继续暴露固定凭据。
- `app/dependencies.py:43` 直接信任 JWT 中的 `isRoot` 和角色声明。

影响：

- 固定 HS256 密钥泄露后可伪造授权声明。
- 数据库和 Redis 凭据应按已泄露处理，而不是只从最新提交删除。
- `.env` 还会进入 Docker build context；使用远程 builder 时风险更高。

处理：

1. 先轮换数据库、Redis、JWT、MinIO、邮件等全部凭据，并撤销现有会话。
2. 执行 `git rm --cached .env`，保留 `.gitignore` 规则。
3. 评估使用 `git filter-repo` 清理历史；公开仓库需要协调历史重写和强制推送。
4. `.env.example` 只保留明显占位符，不提供可工作的公共密码。
5. 生产必填密钥使用 `SecretStr`，缺失或强度不足时拒绝启动。
6. 增加 secret scanning，例如 Gitleaks，并作为 CI 必过项。

### P0-02：公开认证接口存在直接绕过

证据：

- `app/auth/service.py:36` 的短信登录没有校验 `code`。
- `app/auth/router.py:21` 仅在验证码 ID 和验证码值同时存在时校验，省略两者即可绕过。
- `app/tool/wxma/service.py:16` 自行拼接 openid。
- `app/tool/wxma/service.py:32` 忽略微信 code，登录硬编码手机号。
- `app/tool/wxma/service.py:44` 信任调用方传入的 openid、手机号和短信码并创建用户。
- `app/system/user/service.py:243`、`:268` 的手机和邮箱绑定忽略验证码。

影响：知道手机号即可获取他人令牌；占位的微信接口会签发真实令牌；验证码无法承担防爆破和敏感变更校验职责。

处理：

- 在第三方服务完成前，生产默认不注册这些路由，或明确返回 `501 Not Implemented`。
- 验证码必须绑定手机号/邮箱、业务用途、用户、TTL、尝试次数，并原子校验后删除。
- 登录验证码字段改为成组必填；启用条件由服务端配置决定，不能由客户端省略决定。
- 登录、发送验证码、刷新 Token 分别设置严格限流；生产默认开启限流。

### P0-03：Token 生命周期在两种会话模式下均不可靠

已复现：

1. JWT 版本默认值为字符串 `"1"`，版本键首次 `INCR` 仍得到 `1`。第一次登出/踢下线后，旧 Token 仍有效；第二次才失效。
2. JWT refresh 后只保留 `userId`，`username`、`deptId`、`roles`、`dataScopes`、`isRoot` 全部丢失。
3. Redis-Token 登录会对包含 `set` 的 `model_dump()` 调用 `orjson.dumps()`，直接触发 `TypeError: Type is not JSON serializable: set`。
4. Redis-Token 登出只删除 access token，不删除 refresh token；踢人也没有清理用户 refresh token。
5. refresh 不回源校验用户是否已禁用、删除或被移除角色。

证据：`app/auth/token.py:85`、`:139`、`:156`、`:184`、`:225`、`:233`。

处理：

- refresh 必须原子消费旧 refresh token，然后按 `userId` 从数据库重新加载有效用户、角色和数据范围，再签发新令牌对。
- 统一维护 `access_jti`、`refresh_jti`、token family 和 `auth_version`。
- 用户禁用、删除、改密、角色调整、角色状态/菜单/数据范围变化时，统一递增 `auth_version` 或撤销对应 token family。
- `ALLOW_MULTI_LOGIN` 要落实为清晰策略：单设备登出只撤销当前令牌对；踢人撤销用户所有令牌族。
- JWT 和 Redis-Token 必须共享同一组契约测试，保证行为一致。

### P0-04：通知目标用户隔离失效

证据：

- `app/system/notice/router.py:227` 的“我的通知”查询只按 `notice_id` 关联 `SysUserNotice`，没有 `SysUserNotice.user_id == 当前用户`。
- 查询没有限制通知必须分配给当前用户，任何已登录用户可看到全部已发布通知，包括指定用户通知。
- `app/system/notice/router.py:97` 的详情接口不检查发布状态和目标用户关系，可按 ID 读取草稿或他人通知。

影响：定向通知可能跨用户泄露；列表会因关联其他用户的未读记录而重复，读取状态也可能来自其他用户。

处理：

- “我的通知”使用 inner join，并同时限定 `SysUserNotice.user_id == user_id`。
- 详情 dependency 先校验当前用户是否存在对应 `SysUserNotice`；管理端详情使用独立权限接口。
- 发布记录、撤回、读取全部增加事务和并发测试。

### P0-05：README 宣称的 Docker 快速启动链无法形成可用系统

证据：

- 缺少 `uv.lock`，但 `Dockerfile:6` 执行 `uv sync --frozen --no-dev`。
- builder 该阶段只复制 `pyproject.toml`，尚未复制 README 和项目源码。
- Compose 不执行 SQL 初始化或 Alembic migration，新数据卷得到空数据库。
- 镜像没有复制 `alembic/` 和 `sql/`。
- API 容器未设置 `MINIO_ENDPOINT=minio:9000`，会继续访问容器自身的 `localhost:9000`。
- 缺少 `.dockerignore`，当前构建上下文包含 `.venv`、`.git` 和 `.env`。

处理：提交锁文件、修正 Docker 分层、加入 migration 服务、补健康检查和 `.dockerignore`，并在全新数据卷上将 `docker compose up` 纳入 CI 验证。

## 6. P1：高优先级正确性与架构问题

### P1-01：ORM 到 camelCase Schema 的转换普遍错误

项目多处直接执行：

```python
Schema.model_validate(orm_obj, from_attributes=True)
```

但 ORM 属性是 `snake_case`，Schema 字段是 `camelCase`。Pydantic 不会自动把 `config_name` 映射为 `configName`。

已复现：

| 场景 | 实际结果 |
|---|---|
| `ConfigVO.model_validate(SysConfig)` | `configName/configKey/configValue` 均为空字符串 |
| `ConfigForm.model_validate(SysConfig)` | 缺少 3 个必填字段，抛出 ValidationError |
| `DictVO.model_validate(SysDict)` | `dictCode` 为空 |
| `DictUpdate.model_validate(SysDict)` | `dictCode` 校验失败 |
| `DeptUpdate.model_validate(SysDept)` | `parentId` 使用默认 0，而不是 ORM 的 `parent_id` |
| `LogVO.model_validate(SysLog)` | `actionType/requestUri/requestMethod` 等字段丢失 |

受影响模块至少包括 `config`、`dict`、`dept`、`log` 和部分 `notice`。

建议二选一，并全项目统一：

1. 按当前项目规范保留 Schema camelCase 字段，引入全局 `ApiModel`，使用 Pydantic v2 `AliasGenerator` 将验证别名转为 snake_case，同时允许按字段名接收 camelCase。
2. 对复杂 VO 明确实现 `_to_vo` / `_to_form`，像 `UserService` 一样手工映射。

禁止继续假设 `from_attributes=True` 会完成命名风格转换。每个 ORM -> Schema 转换必须有契约测试。

### P1-02：OpenAPI 没有响应契约

全仓路由没有 `response_model`，也基本没有返回类型标注。实测登录和用户列表的成功响应 schema 均为 `{}`，错误响应仍显示 FastAPI 默认 `HTTPValidationError`，与运行时自定义 `Result` 不一致。

处理：

- 路由增加 `response_model=Result[UserVO]`、`Result[PageResult[UserVO]]` 等明确模型。
- 为 401/403/404/409/422/500 统一声明错误响应模型。
- 创建接口根据兼容要求评估返回 201；至少保证项目自定义的 HTTP/业务码双轨一致。
- 验证码失败应抛 `BusinessException`，不能返回 HTTP 200 + 错误业务码。

### P1-03：鉴权不是默认拒绝，多个管理接口匿名可访问

OpenAPI 中未声明安全要求的接口包括：

- 代码生成的表清单、配置读取/删除、预览和下载。
- 系统配置表单和任意 key 的值。
- 日志统计、角色菜单 ID、用户/角色下拉选项。
- SSE 在线人数、多个字典管理表单。

处理：

- 管理域 router 默认添加 `dependencies=[Depends(require_perm())]`。
- 在默认登录校验之上，为变更和敏感读取追加精确权限。
- 公开配置另建白名单接口，只返回前端确实需要且确认不敏感的键。
- 代码生成器生产默认关闭，并为查看、预览、下载、更新、删除分别设置权限。

### P1-04：数据权限 fail-open，部门路径维护错误

证据：

- `app/system/role/data_permission.py:11` 明确规定无 scope 时不过滤。
- 未知 dataScope、缺少部门、缺少过滤列等情况都可能返回“不加 WHERE”。
- `RoleCreate.dataScope` 允许 `None`。
- `app/system/dept/service.py:79` 创建子部门时把新部门 ID 写入 `tree_path`，而种子数据语义要求写父部门祖先路径。
- 修改部门父节点时没有更新自身及子树路径。

影响：角色配置缺失时可能获得全量数据；部门移动后旧上级可能继续看到不属于自己的数据，新上级反而不可见。

处理：

- 非超管遇到缺失或非法数据范围必须返回 `false()`，即 fail closed。
- dataScope 改为必填枚举，数据库列改为 `NOT NULL` 并加 check constraint。
- 统一 `tree_path` 语义，创建时使用父节点 ID 路径，移动时事务内重算整棵子树。
- 禁止把节点移动到自身或后代；增加并发和权限回归测试。
- 数据量增长后可评估 PostgreSQL recursive CTE、`ltree` 或闭包表。

### P1-05：角色和用户安全变更没有完整撤销旧会话

当前只在角色 data_scope 或自定义部门变化时撤销会话。角色菜单变化、角色禁用/删除、用户禁用/删除、改密、移除角色等操作不会统一撤销旧 Token。

同时，`PermissionChecker` 信任 Token 中的角色编码，再查询这些角色是否拥有权限，没有按当前 `user_id` 重新确认用户仍属于这些角色。

处理：建立单一 `AuthorizationVersionService`，所有安全属性变化都调用同一入口；权限检查至少校验当前用户状态和授权版本，避免各 service 自行决定是否踢人。

### P1-06：固定路由被动态路由遮蔽

`PUT /api/v1/notices/read-all` 实际首先匹配 `PUT /api/v1/notices/{notice_id}`，进入 `update_notice`。这已通过 Starlette 路由匹配复现。

处理：将 `/read-all` 放到所有 `/{notice_id}` PUT 路由之前，并增加自动检查：对同一 router 中的后置固定路径执行匹配测试，防止被前置动态路径捕获。

### P1-07：CORS 默认配置不可用

`app/middleware.py:18` 把逗号分隔的多个 Origin 传给 `allow_origin_regex`。在 `DEBUG=false` 下，两个默认前端 Origin 的预检请求均返回 400。

处理：

- Settings 使用 `list[str]` 表达允许域名。
- 传入 `allow_origins=settings.allowed_origins`。
- 仅在明确需要时使用受控正则；不能把 CSV 当正则。
- 增加允许域名、拒绝域名、credentials 和 OPTIONS 预检测试。

### P1-08：数据库迁移和完整性约束缺失

- `alembic/versions/` 为空，无法增量升级或回滚。
- SQL 初始化脚本没有外键，多个关联表的 ORM 外键也不完整。
- `Base.metadata` 没有约束命名 convention。
- 部分唯一性仅由“先查再写”保证，存在并发竞争。
- SQL 脚本、ORM 和运行逻辑已有状态语义漂移，例如 `sys_dict.status` 的注释、默认值和种子数据不一致。

处理：

1. 为现有 schema 建立 baseline revision。
2. 既有数据库使用 `alembic stamp <baseline>`，新库从 `upgrade head` 创建。
3. 增加 PK/FK/UQ/CK/Index 命名 convention。
4. 用数据库约束保证唯一性，捕获 `IntegrityError` 映射为 `DUPLICATE_KEY`。
5. CI 在空库执行 upgrade、downgrade、再次 upgrade。

### P1-09：测试与质量门禁不能执行

- 当前虚拟环境缺少全部开发依赖。
- README 使用无版本 `pip install`，当前环境中 bcrypt、redis、sse-starlette、Pillow 已超出 pyproject 范围，Alembic则完全缺失。
- 两个现有测试路径已失效：`/api/v1/auth/users/me` 和 `/api/v1/swagger-ui.html` 均返回 404。
- `ResultCode` 测试假设 `str(Enum) == value`，当前 Python 实际返回 `ResultCode.SUCCESS`。
- 验证码测试会访问真实 Redis，没有 dependency override。

处理：统一使用 `uv sync --frozen --extra dev`，提交 `uv.lock`；测试使用独立 PostgreSQL/Redis 或依赖覆盖，禁止访问共享环境。

## 7. P2：维护性、性能与可观测性

### 7.1 模块拆分

保持当前 `system/`、`tool/` 分组，不做全量扁平化。优先拆分：

- `app/system/notice/router.py`：Schema、Service、Router 混合，且有复杂查询和 11 个端点。
- `app/system/config/router.py`：Schema、Service、Router 混合，共 7 个端点。
- `app/system/log/router.py`：查询、统计、Schema、Router 混合。
- `app/tool/file/router.py`：可将存储客户端、校验和业务权限移到 service。
- 为 `app/tool/codegen`、`app/tool/wxma` 补 `__init__.py`。

### 7.2 性能与韧性

- bcrypt 的 hash/check 是 CPU 密集操作，当前直接运行在 async service 内；应使用 `run_in_threadpool`，批量导入还需限制并发。
- 用户导入和文件上传一次性读入内存，应改为流式读取、尽早限额并限制行数/解压大小。
- 文件类型不能只信任扩展名，应检查 MIME/文件签名；删除必须按文件 ID 做对象级权限校验。
- SSE 每个连接使用无界队列，应设置 `maxsize`、丢弃/断开策略和慢消费者指标。
- 角色列表为每个角色追加菜单和部门查询，存在 N+1，应批量加载。
- 4 worker 配合 `pool_size=20`、`max_overflow=10`，理论最大 120 个数据库连接，超过 PostgreSQL 默认 100。按公式控制：

```text
workers * (pool_size + max_overflow) + 运维连接余量 <= max_connections * 80%
```

### 7.3 可观测性

- 将 `/health` 拆成 `/live` 和 `/ready`；readiness 检查数据库和 Redis，并设置短超时。
- 实际应用 `LOG_LEVEL`，增加 request ID、结构化字段和敏感信息脱敏。
- 增加 Prometheus 指标或 OpenTelemetry：请求耗时、错误率、DB 池、Redis、Token refresh、SSE 队列和文件上传。
- `operation_log` 当前全仓未使用；启用时应使用独立事务或 outbox，不能因日志写入失败污染主业务事务。

### 7.4 文档与治理

- README 结构树与实际 `system/`、`tool/` 目录不一致。
- README 声称 Apache 2.0，pyproject 声明 MIT，仓库没有 LICENSE。
- README 快速开始绕过 pyproject/uv，导致依赖漂移。
- 中英文 README 应同步更新目录、迁移、测试、Docker、文档地址和许可证。

## 8. 建议目标结构

不建议重新引入 `core/common/framework/modules`。目标是在现有结构上补齐域内文件和工程目录：

```text
youlai-fastapi/
├── app/
│   ├── main.py
│   ├── config.py                 # 根配置聚合与环境校验
│   ├── schemas.py                # ApiModel / alias / datetime 序列化
│   ├── database.py
│   ├── redis.py
│   ├── response.py
│   ├── exceptions.py
│   ├── pagination.py
│   ├── constants.py
│   ├── dependencies.py
│   ├── middleware.py
│   ├── registry.py
│   ├── auth/
│   │   ├── config.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── token.py
│   │   └── utils.py
│   ├── captcha/
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── constants.py
│   ├── system/
│   │   ├── user|role|menu|dept|dict/   # 保持现状
│   │   ├── config/{models,schemas,service,router}.py
│   │   ├── notice/{models,schemas,service,router}.py
│   │   └── log/{models,schemas,service,router,constants,operation_log}.py
│   └── tool/
│       ├── file/{router,schemas,service}.py
│       ├── codegen/{__init__,router,schemas,service}.py
│       ├── wxma/{__init__,config,router,schemas,service}.py
│       └── sse/{router,manager,topics}.py
├── alembic/versions/<yyyy-mm-dd>_<slug>.py
├── tests/
│   ├── conftest.py
│   ├── test_openapi.py
│   ├── test_registry.py
│   ├── auth/
│   ├── system/<domain>/
│   └── tool/<domain>/
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── .dockerignore
├── uv.lock
├── LICENSE
└── README.md
```

## 9. 分阶段落地方案

| 阶段 | 建议周期 | 主要工作 | 退出标准 |
|---|---|---|---|
| Phase 0：安全止血 | 1-2 天 | 轮换密钥、取消跟踪 `.env`、关闭短信/WX占位接口、修 CORS、限制匿名管理接口 | 无已知可利用认证绕过；secret scan 通过 |
| Phase 1：权限正确性 | 3-5 天 | 重构 Token refresh/revoke、通知 ACL、数据权限 fail-closed、修复 tree_path | JWT/Redis 双模式契约测试通过；部门移动权限回归通过 |
| Phase 2：API 契约 | 1 个迭代 | 统一 ApiModel/显式映射、补 response_model、修固定路由顺序、拆 notice/config/log | OpenAPI 成功响应不再是 `{}`；ORM/Schema 契约测试通过 |
| Phase 3：工程闭环 | 1 个迭代 | `uv.lock`、Alembic baseline、Docker/Compose、测试隔离、CI/pre-commit | 全新环境一条命令启动；CI lint/type/test/build/migration 全绿 |
| Phase 4：性能与运维 | 持续 | 上传流式化、bcrypt 线程池、SSE 背压、连接池预算、指标与追踪 | 压测和故障演练达到项目 SLO |

## 10. 测试与 CI 最低基线

### 10.1 测试分层

1. **纯单元测试**
   - ResultCode、Pydantic alias、tree_path、data scope、Token 编解码。
2. **Service 集成测试**
   - 使用独立 PostgreSQL transaction；覆盖唯一约束、软删、角色关系和并发写入。
3. **Router 契约测试**
   - 使用 `httpx.AsyncClient` 和 `dependency_overrides` 替换 auth、Redis、第三方服务。
4. **端到端 smoke**
   - 新数据库执行 `alembic upgrade head`，启动 API，验证登录、用户、权限、文件和通知关键路径。

### 10.2 必须新增的回归用例

- 第一次 logout 后旧 access token 立即失效。
- refresh 后角色、部门、data scope、root 标识正确，且旧 refresh token 不可重放。
- Redis-Token 与 JWT 模式行为一致。
- 禁用/删除/改密/移除角色后旧会话失效。
- 非目标用户不能读取定向通知。
- dataScope 缺失或非法时不返回任何业务数据。
- 新建/移动部门后，本部门及子部门权限正确。
- `/read-all` 匹配固定路由。
- ORM snake_case 到 Schema camelCase 的所有字段映射正确。
- 生产 CORS 只允许白名单 Origin。
- 匿名访问代码生成、配置和管理表单返回 401/403。

### 10.3 CI 命令建议

```bash
uv sync --frozen --extra dev
uv run ruff format --check app tests
uv run ruff check app tests
uv run mypy app
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70
uv run alembic upgrade head
docker compose config --quiet
docker build .
```

认证、授权和数据权限模块建议达到 90% 以上分支覆盖率；全项目可以先从 70% 门槛开始，逐步提高。

## 11. Docker 与部署目标

1. 提交 `uv.lock`，Docker builder 先复制 `pyproject.toml`、`uv.lock`、README，再执行 frozen sync。
2. 添加 `.dockerignore`，排除 `.git`、`.venv`、`.env`、缓存、覆盖率和本地文档图片。
3. 运行镜像使用非 root 用户，设置只读文件系统和最小 Linux capabilities。
4. 增加 migration/init 服务，API 只在 migration 成功且 PostgreSQL/Redis healthy 后启动。
5. API 显式配置 `MINIO_ENDPOINT=minio:9000`，生产不暴露数据库和 Redis 宿主机端口。
6. `/live` 用于容器存活，`/ready` 用于流量接入；Docker 和编排平台分别使用对应探针。
7. 数据库和 Redis 增加 connect/read/write timeout，并按 worker 数配置连接池。
8. 在 CI 使用全新 volume 验证 `docker compose up` 后 readiness、迁移版本和基础 API。

## 12. 不建议的优化方向

- 不要为了形式对齐把 `system/*` 和 `tool/*` 全部重新扁平化，当前分组有明确业务语义。
- 不要引入通用 Repository 层包装所有 SQLAlchemy 操作；当前 service 直接表达查询更清晰。
- 不要自动扫描文件注册 router/model；保留显式注册，并用测试防止漏注册。
- 不要继续扩大单一 `Settings`，也不要把所有共享代码塞入 `common`。
- 不要用 HTTP 200 包装所有错误；保持 HTTP 状态码与业务码双轨。
- 不要先做格式化和大规模重命名，再修安全和正确性问题。

## 13. 最终验收清单

### 安全

- [ ] 历史泄露凭据已轮换，旧凭据不可用。
- [ ] `.env` 不再被 Git 跟踪，secret scan 通过。
- [ ] 短信/WX/验证码接口不存在占位放行。
- [ ] JWT 和 Redis-Token refresh、logout、kick-out 契约测试通过。
- [ ] 所有管理接口默认需要登录，敏感操作有精确权限。
- [ ] 定向通知和文件删除具备对象级权限校验。
- [ ] 数据权限在异常配置下 fail closed。

### 正确性

- [ ] 所有 ORM -> Schema 转换有明确别名或手工映射。
- [ ] OpenAPI 成功和错误响应模型与运行时一致。
- [ ] 固定路由不会被动态路由遮蔽。
- [ ] 部门/菜单移动会维护整棵子树路径并阻止环。
- [ ] 用户和角色安全属性变化会立即撤销旧授权。

### 工程化

- [ ] `uv.lock`、CI、pre-commit、LICENSE、`.dockerignore` 已提交。
- [ ] Alembic 有 baseline 和后续 revision，空库可 upgrade/downgrade。
- [ ] 测试不访问共享数据库、Redis 或第三方服务。
- [ ] Ruff、Mypy、pytest、Docker build 和 migration smoke 均为 CI 门禁。
- [ ] 全新环境可按 README 一次启动并通过 readiness。

### 运维

- [ ] 数据库连接总预算低于实例上限的 80%。
- [ ] 上传采用流式限制，SSE 有背压策略。
- [ ] 日志级别、request ID、脱敏、指标和告警已生效。
- [ ] 生产环境默认关闭 Swagger/Redoc，按环境显式开启。

## 14. 建议执行顺序

最稳妥的顺序是：

1. 先处理凭据和直接认证绕过。
2. 再修 Token、通知 ACL、data scope 和 tree_path。
3. 用回归测试固定安全行为。
4. 再统一 Schema、OpenAPI 和路由鉴权。
5. 最后补锁文件、迁移、Docker、CI，并进行模块拆分和性能优化。

这一顺序能最大限度减少行为漂移，避免在安全缺陷仍存在时投入大量目录和格式调整。
