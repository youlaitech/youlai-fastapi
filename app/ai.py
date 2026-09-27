"""AI 对话：OpenAI 兼容的 chat/completions 调用与提示词加载。"""
import json
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.exceptions import BusinessException
from app.response import ResultCode

logger = logging.getLogger(__name__)

# 提示词目录，各模块的 md 提示词集中放在动态表单模块下
PROMPTS_DIR = Path(__file__).resolve().parent / "system" / "form" / "prompts"


def load_prompt(name: str) -> str:
    """读取提示词文件，文件不存在时返回数据不存在错误。"""
    path = PROMPTS_DIR / name
    if not path.exists():
        raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg=f"提示词不存在：{name}")
    return path.read_text(encoding="utf-8").strip()


async def chat(system_prompt: str, user_prompt: str) -> str:
    """调用 AI 对话接口，返回去掉代码围栏的文本内容。"""
    if not settings.AI_ENABLED:
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="AI 功能未开启，请配置 AI_ENABLED 与 AI_API_KEY")

    url = f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url, json=payload, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}
        )
    if response.status_code != 200:
        logger.error("AI 调用失败 %s: %s", response.status_code, response.text)
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=f"AI 调用失败：{response.status_code}")

    content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    return _strip_code_fence(content)


async def chat_json(system_prompt: str, user_prompt: str) -> dict:
    """调用 AI 对话接口，把返回内容解析为字典。"""
    content = await chat(system_prompt, user_prompt)
    try:
        result = json.loads(content)
    except ValueError:
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="AI 返回内容不是合法 JSON")

    if not isinstance(result, dict):
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="AI 返回内容不是合法 JSON 对象")
    return result


def _strip_code_fence(content: str) -> str:
    """去掉模型输出里可能包裹的 json 代码围栏。"""
    text = (content or "").strip()
    if not text.startswith("```"):
        return text
    start = text.find("\n")
    end = text.rfind("```")
    return text[start + 1:end].strip() if start != -1 and end > start else text
