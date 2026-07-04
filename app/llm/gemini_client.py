"""
Groq LLM client — thin async wrapper around the Groq REST API.

Provides structured prompting for planning, content generation, and reflection.
Includes retry logic with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────

_API_KEY = os.getenv("GROQ_API_KEY", "")
_MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
_MAX_RETRIES = 5
_BACKOFF_BASE = 3  # seconds


def _validate_key() -> None:
    """Ensure an API key is configured."""
    if not _API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Get a free key at https://console.groq.com and add it to your .env file."
        )


# ── Core call with retry ─────────────────────────────────────────────

async def call_gemini(
    prompt: str,
    *,
    system_instruction: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 8192,
) -> str:
    """
    Send a prompt to Groq and return the text response.

    NOTE: Function is still named `call_gemini` to avoid changing all
    import sites — it's a drop-in replacement.

    Retries up to _MAX_RETRIES times with exponential backoff on transient
    errors (rate-limit, network, server errors).
    """
    _validate_key()

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": _MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }

    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    _BASE_URL,
                    json=payload,
                    headers=headers,
                )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            # Rate limit — wait and retry
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", _BACKOFF_BASE ** attempt))
                logger.warning(
                    "Rate limited (attempt %d/%d) — retrying in %ds",
                    attempt, _MAX_RETRIES, retry_after,
                )
                await asyncio.sleep(retry_after)
                continue

            # Other errors
            error_msg = response.text[:500]
            raise RuntimeError(
                f"Groq API error {response.status_code}: {error_msg}"
            )

        except httpx.HTTPError as exc:
            last_error = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "Groq call failed (attempt %d/%d): %s — retrying in %ds",
                attempt, _MAX_RETRIES, exc, wait,
            )
            await asyncio.sleep(wait)

        except RuntimeError:
            raise

        except Exception as exc:
            last_error = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "Groq call failed (attempt %d/%d): %s — retrying in %ds",
                attempt, _MAX_RETRIES, exc, wait,
            )
            await asyncio.sleep(wait)

    raise RuntimeError(
        f"Groq call failed after {_MAX_RETRIES} attempts: {last_error}"
    )


# ── JSON extraction helper ───────────────────────────────────────────

def extract_json(text: str) -> Any:
    """
    Extract JSON from an LLM response that may contain markdown fences
    or surrounding prose.
    """
    # Try to find a fenced code block first
    fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if fence_match:
        return json.loads(fence_match.group(1))

    # Fall back to finding the first { ... } or [ ... ]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:300]}")
