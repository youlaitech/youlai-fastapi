"""注册全部域模型到 Base.metadata — 供 alembic autogenerate 与跨域 relationship 解析。

各域模型按业务域拆分在 app/system/<domain>/models.py；集中导入使
Base.metadata 收集所有表。`import app.registry` 即触发全部注册。
"""

from app.system.config import models as _config_models  # noqa: F401
from app.system.dept import models as _dept_models  # noqa: F401
from app.system.dict import models as _dict_models  # noqa: F401
from app.system.log import models as _log_models  # noqa: F401
from app.system.menu import models as _menu_models  # noqa: F401
from app.system.notice import models as _notice_models  # noqa: F401
from app.system.role import models as _role_models  # noqa: F401
from app.system.user import models as _user_models  # noqa: F401
from app.tool.codegen import models as _codegen_models  # noqa: F401
