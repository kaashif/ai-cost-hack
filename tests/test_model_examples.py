from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from costhack.schema import Case
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


class RecordingCompletions:
    calls = 0

    def create(self, **kwargs: object) -> object:
        assert kwargs["model"] == "gpt-5.5"
        assert kwargs["extra_body"] == {"project_id": "event-project"}
        self.calls += 1
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "risk": "low",
                                "findings": [],
                                "tests": [],
                                "next_action": "approve",
                            }
                        )
                    )
                )
            ]
        )


class RecordingOpenAI:
    completions = RecordingCompletions()

    def __init__(self, **kwargs: object) -> None:
        assert kwargs["api_key"] == "mg_test"
        assert kwargs["base_url"] == "https://api-gateway.merge.dev/v1/openai"
        self.chat = SimpleNamespace(completions=self.completions)


def test_merge_only_example_creates_its_own_client() -> None:
    with (
        patch.dict(
            "os.environ",
            {
                "MERGE_GATEWAY_API_KEY": "mg_test",
                "MERGE_GATEWAY_PROJECT_ID": "event-project",
            },
        ),
        patch("costhack.model_strategy.OpenAI", RecordingOpenAI),
    ):
        merge_review(example_case())

    assert RecordingOpenAI.completions.calls == 1
