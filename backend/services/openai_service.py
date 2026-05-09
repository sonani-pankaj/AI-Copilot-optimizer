# See: specs/backend/query-endpoint.md, review-endpoint.md — OpenAI Client
import logging
import os
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# LLM_MODEL defaults to gpt-4.1-mini but can be overridden to any Ollama model
# e.g. LLM_MODEL=llama3.2  OPENAI_BASE_URL=http://localhost:11434/v1  OPENAI_API_KEY=ollama
_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1-mini")
_MAX_TOKENS = 300

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")
        base_url = os.environ.get("OPENAI_BASE_URL")  # None → default OpenAI endpoint
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


_SYSTEM_PROMPTS = {
    "QUERY": (
        "You are a concise senior Java engineer. "
        "Answer the code question clearly and briefly. "
        "Focus on Spring Boot, Spring Batch, Servlets, and JSP patterns."
    ),
    "GENERATE_TESTS": (
        "You are a Java testing expert. "
        "Generate JUnit 5 unit tests for the provided code. "
        "Use Mockito for mocks. Cover edge cases. Keep tests minimal but complete. "
        "Return only the test class code."
    ),
    "REVIEW": (
        "You are a senior Java code reviewer. "
        "Analyze the provided git diff and return ONLY valid JSON matching this schema: "
        '{"bugs":[{"severity":"HIGH|MEDIUM|LOW","category":"bug","description":"...","line_hint":"..."}],'
        '"performance":[...],"security":[...],"summary":"..."}. '
        "No markdown, no explanation, only JSON."
    ),
}


async def complete(prompt: str, prompt_type: str = "QUERY") -> tuple[str, int]:
    """Call OpenAI and return (response_text, tokens_used).

    Raises RuntimeError on API failure so callers can return 502.
    """
    system = _SYSTEM_PROMPTS.get(prompt_type, _SYSTEM_PROMPTS["QUERY"])
    model = os.environ.get("LLM_MODEL", _MODEL)
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": _MAX_TOKENS if prompt_type != "REVIEW" else 500,
        "temperature": 0.2,
    }
    if prompt_type == "REVIEW":
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = await _get_client().chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        return content.strip(), tokens
    except Exception as exc:
        logger.error("OpenAI API error: %s", exc)
        raise RuntimeError(f"LLM unavailable: {exc}") from exc
