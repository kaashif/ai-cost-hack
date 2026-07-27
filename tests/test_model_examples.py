from __future__ import annotations

import json
from collections.abc import Mapping

from costhack.schema import Case, Message, ModelResponse
from examples.merge_only.strategy import review as merge_review


def example_case() -> Case:
    return {
        "id": "public-example",
        "title": "Example",
        "brief": "Review the change.",
        "context": [{"kind": "diff", "path": "example.py", "content": "VALUE = 1"}],
        "rubric": {
            "risk": "low",
            "next_action": "approve",
            "pass_score": 80,
            "must_find": [],
            "required_test_terms": [],
            "required_findings": [],
        },
    }


class RecordingClient:
    calls = 0

    def __init__(self) -> None:
        self.compressions: list[str] = []

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        max_output_tokens: int = 1200,
        compression: str = "none",
        compression_rate: float | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> ModelResponse:
        del messages, max_output_tokens, compression_rate, tags
        assert model == "openai/gpt-5.5"
        self.calls += 1
        self.compressions.append(compression)
        return {
            "text": json.dumps(
                {
                    "risk": "low",
                    "findings": [],
                    "tests": [],
                    "next_action": "approve",
                }
            ),
            "model": model,
            "usage": {},
        }


def test_merge_only_example() -> None:
    client = RecordingClient()

    merge_review(example_case(), client)

    assert client.calls == 1
    assert client.compressions == ["none"]
