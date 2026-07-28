"""Shared implementation for the public Merge-powered examples."""

from __future__ import annotations

import json
import os
from typing import TypedDict

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from .contract import validate_review
from .schema import Case, ContextSection, Review

MODEL = "gpt-5.5"


class VisibleCase(TypedDict):
    title: str
    brief: str
    context: list[ContextSection]


def parse_review(text: str) -> Review:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline == -1:
            raise ValueError("model returned an incomplete code fence")
        cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return validate_review(json.loads(cleaned.strip()))


def review_messages(case: Case) -> list[ChatCompletionMessageParam]:
    visible_case: VisibleCase = {
        "title": case["title"],
        "brief": case["brief"],
        "context": case["context"],
    }
    return [
        {
            "role": "system",
            "content": (
                "Review this proposed software change as a release gate. Return only one "
                "JSON object with keys risk, findings, tests, and next_action. risk and "
                "each finding severity must be low, medium, high, or critical. "
                "next_action must be approve, request_changes, or block. findings must "
                "be an array of at most 8 objects; each needs category, severity, file, "
                "evidence, and explanation. tests must be an array of plain strings. "
                "Use exact file paths and quote decisive code or context verbatim in "
                "evidence. Use only these categories: authorization, authentication, "
                "data_integrity, data_loss, dependency, idempotency, injection, "
                "observability, privacy, race_condition, reliability, testing_gap, "
                "validation. Map missing ownership checks to authorization; unsafe "
                "schema changes to data_integrity; shell execution to injection; "
                "committed secrets and cross-tenant disclosure to privacy; disabled TLS "
                "verification to validation; duplicate retry side effects to "
                "idempotency; tests that did not execute to testing_gap; vulnerable "
                "transitive packages to dependency; and incorrect timezone conversion "
                "to data_loss. Use block for an exploitable or destructive defect. "
                "Use request_changes for a fixable high-risk release defect. Report the "
                "root defect only; do not add a separate testing_gap finding merely "
                "because tests failed to cover that same defect. Propose tests with "
                "concrete inputs and expected outcomes. Avoid unsupported findings."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(visible_case, separators=(",", ":")),
        },
    ]


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for Merge Gateway model calls")
    return value


def review_with_model(case: Case) -> Review:
    client = OpenAI(
        api_key=_required_env("MERGE_GATEWAY_API_KEY"),
        base_url="https://api-gateway.merge.dev/v1/openai",
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=review_messages(case),
        max_completion_tokens=1600,
        extra_body={
            "project_id": _required_env("MERGE_GATEWAY_PROJECT_ID"),
        },
    )
    return parse_review(response.choices[0].message.content or "")
