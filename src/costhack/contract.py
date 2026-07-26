"""Shared JSON-compatible challenge contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from .schema import Action, Message, ModelResponse, Review, Risk

RISKS: tuple[Risk, ...] = ("low", "medium", "high", "critical")
ACTIONS: tuple[Action, ...] = ("approve", "request_changes", "block")
CATEGORIES = (
    "authorization",
    "authentication",
    "data_integrity",
    "data_loss",
    "dependency",
    "idempotency",
    "injection",
    "observability",
    "privacy",
    "race_condition",
    "reliability",
    "testing_gap",
    "validation",
)


class ContractError(ValueError):
    """Raised when a submission returns an invalid review."""


def validate_review(review: object) -> Review:
    if not isinstance(review, Mapping):
        raise ContractError("review must be an object")
    risk = review.get("risk")
    if risk not in RISKS:
        raise ContractError(f"risk must be one of {', '.join(RISKS)}")
    action = review.get("next_action")
    if action not in ACTIONS:
        raise ContractError(f"next_action must be one of {', '.join(ACTIONS)}")
    findings = review.get("findings")
    if not isinstance(findings, list) or len(findings) > 8:
        raise ContractError("findings must be a list of at most 8 items")
    for index, finding in enumerate(findings):
        if not isinstance(finding, Mapping):
            raise ContractError(f"finding {index} must be an object")
        for field in ("category", "severity", "file", "evidence", "explanation"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise ContractError(f"finding {index}.{field} must be a non-empty string")
        if finding["severity"] not in RISKS:
            raise ContractError(f"finding {index}.severity is invalid")
    tests = review.get("tests")
    if not isinstance(tests, list) or not all(isinstance(item, str) for item in tests):
        raise ContractError("tests must be a list of strings")
    return cast(Review, review)


@dataclass
class OfflineModelClient:
    """Model client used by the zero-spend public starter."""

    calls: int = 0

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
        raise RuntimeError(
            "The public benchmark is offline. Use deterministic logic or run with the "
            "event's metered model client."
        )
