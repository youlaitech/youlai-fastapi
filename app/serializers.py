"""自定义序列化类型。

BigId：整数 id 标记类型，JSON 序列化时输出字符串，避免前端 JS 大数精度丢失。
输入接受 int 或数值字符串。
"""

from pydantic_core import core_schema


class BigId(int):
    """整型主键/外键标记类，JSON 序列化时输出字符串，避免前端 JS 大数精度丢失。"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        def _validate(v):
            if v is None:
                return None
            if isinstance(v, cls):
                return v
            return cls(int(v))

        def _serialize(v):
            return str(v) if v is not None else None

        return core_schema.no_info_plain_validator_function(
            _validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize, return_schema=core_schema.str_schema()
            ),
        )
