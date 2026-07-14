"""密码哈希与加密工具。"""

import bcrypt


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希，返回可用于存储的密文字符串。"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配。"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
