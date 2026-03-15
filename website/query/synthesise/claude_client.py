"""
Anthropic Claude client for synthesis.
Supports both streaming and non-streaming responses.
"""
import sys
from pathlib import Path
from typing import Iterator, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "website"))
from query.config import LLM_MODEL


def synthesize(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
) -> str:
    """Non-streaming synthesis. Returns full response text."""
    import anthropic
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


def synthesize_stream(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
) -> Iterator[str]:
    """Streaming synthesis. Yields text chunks as they arrive."""
    import anthropic
    client = anthropic.Anthropic()

    with client.messages.stream(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text
