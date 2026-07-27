"""Demonstration only: Condense proxies directly to OpenAI.

This bypasses Merge Gateway and is therefore not eligible under the event rules.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import TypedDict, cast

from costhack.model_strategy import parse_review, review_messages
from costhack.schema import Case, Message, ModelClient, Review

CONDENSE_OPENAI_URL = "https://api.condense.chat/openai/v1/chat/completions"


class ProxyMessage(TypedDict):
    content: str


class ProxyChoice(TypedDict):
    message: ProxyMessage


class ProxyResponse(TypedDict):
    choices: list[ProxyChoice]


def _proxy_completion(messages: list[Message]) -> str:
    condense_token = os.environ.get("CONDENSE_AUTH_TOKEN", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not condense_token.startswith("ak_"):
        raise RuntimeError("CONDENSE_AUTH_TOKEN must be a Condense ak_ key")
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY is required for the Condense proxy example")

    request = urllib.request.Request(
        CONDENSE_OPENAI_URL,
        data=json.dumps(
            {
                "model": os.environ.get("OPENAI_MODEL", "gpt-5.5"),
                "messages": messages,
                "max_completion_tokens": 1600,
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
            "User-Agent": "patchguard-condense-proxy-example/0.1",
            "X-Condense-Auth-Token": condense_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = cast(ProxyResponse, json.loads(response.read()))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Condense proxy returned HTTP {exc.code}: {detail[:500]}") from exc
    if not payload["choices"]:
        raise RuntimeError("Condense proxy returned no choices")
    return payload["choices"][0]["message"]["content"]


def review(case: Case, client: ModelClient) -> Review:
    del client
    return parse_review(_proxy_completion(review_messages(case)))
