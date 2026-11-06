"""命名转换，供代码生成的目录、路由与权限标识使用"""

import re


def kebab_case(value: str) -> str:
    """snake_case / PascalCase → kebab-case，如 MenuDemo → menu-demo"""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", value.replace("_", "-")).split("-")
    return "-".join(w.lower() for w in words if w)

def pluralize_kebab(value: str) -> str:
    """kebab-case 转英文复数，如 dict-item → dict-items、category → categories"""
    word = kebab_case(value)
    if re.search(r"(s|x|z|ch|sh)$", word):
        return f"{word}es"
    if re.search(r"[^aeiou]y$", word):
        return f"{word[:-1]}ies"
    return f"{word}s"
