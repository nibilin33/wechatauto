from __future__ import annotations

"""
Reply-prompt builder for the auto-reply feature (M4).

Provides a minimal rule-based responder and an LLM prompt template that can be
wired into `send_message` once SendGuard clears the message for sending.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class ReplyContext:
    contact: str
    recent_messages: list[str]
    """Last N messages from the chat (oldest first)."""


# ---------------------------------------------------------------------------
# Rule-based reply (no LLM required)
# ---------------------------------------------------------------------------

_DEFAULT_RULES: list[tuple[list[str], str]] = [
    (["你好", "hello", "hi", "嗨"], "你好！"),
    (["在吗", "在不"], "在的"),
    (["谢谢", "感谢", "thanks"], "不客气~"),
]


def rule_based_reply(ctx: ReplyContext) -> str | None:
    """
    Return a fixed reply if the last message matches a known keyword pattern.
    Returns None if no rule matches (caller should escalate to LLM or skip).
    """
    if not ctx.recent_messages:
        return None
    last = ctx.recent_messages[-1].lower()
    for keywords, response in _DEFAULT_RULES:
        if any(k in last for k in keywords):
            return response
    return None


# ---------------------------------------------------------------------------
# LLM prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是一个微信消息自动回复助手。根据上下文生成简洁、自然的中文回复。
规则：
- 回复简短（不超过50字）
- 语气友好、自然，不要过于正式
- 不涉及金融、转账、验证码、隐私信息
- 如果不确定，回复"稍后回复你"即可
"""


def build_llm_prompt(ctx: ReplyContext) -> list[dict]:
    """
    Build a messages list suitable for OpenAI-compatible chat completions.
    """
    history_text = "\n".join(
        f"[{i + 1}] {msg}" for i, msg in enumerate(ctx.recent_messages)
    )
    user_text = (
        f"联系人：{ctx.contact}\n"
        f"最近消息（共{len(ctx.recent_messages)}条）：\n{history_text}\n\n"
        "请给出简短回复（只输出回复内容，不要解释）："
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]


def llm_reply(
    ctx: ReplyContext,
    *,
    client,  # openai.OpenAI or compatible
    model: str = "gpt-4.1-mini",
    max_tokens: int = 80,
) -> str:
    """
    Call an OpenAI-compatible endpoint and return the reply text.
    """
    messages = build_llm_prompt(ctx)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return (resp.choices[0].message.content or "").strip()
