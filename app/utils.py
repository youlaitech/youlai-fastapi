"""跨模块共用的命名转换工具。"""

import re


def kebab_case(value: str) -> str:
    """snake_case / PascalCase → kebab-case（如 MenuDemo → menu-demo）；接口路径、前端目录与菜单路由共用此实现。"""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", value.replace("_", "-")).split("-")
    return "-".join(w.lower() for w in words if w)

def pluralize_kebab(value: str) -> str:
    """kebab-case 转英文复数（如 dict-item → dict-items、category → categories）；接口路径与前端 baseURL 共用。"""
    word = kebab_case(value)
    if re.search(r"(s|x|z|ch|sh)$", word):
        return f"{word}es"
    if re.search(r"[^aeiou]y$", word):
        return f"{word[:-1]}ies"
    return f"{word}s"
