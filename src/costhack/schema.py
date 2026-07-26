"""Typed boundary shared by submissions and evaluators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, NotRequired, Protocol, TypedDict

Risk = Literal["low", "medium", "high", "critical"]
Action = Literal["approve", "request_changes", "block"]


class ContextSection(TypedDict):
    kind: str
    content: str
    path: NotRequired[str]


class RequiredFinding(TypedDict):
    id: str
    category: str
    file: str
    evidence_anchor: str


class Rubric(TypedDict):
    risk: Risk
    next_action: Action
    pass_score: float
    must_find: list[str]
    required_test_terms: list[str]
    required_findings: list[RequiredFinding]


class Case(TypedDict):
    id: str
    title: str
    brief: str
    context: list[ContextSection]
    rubric: Rubric


class Finding(TypedDict):
    category: str
    severity: Risk
    file: str
    evidence: str
    explanation: str


class Review(TypedDict):
    risk: Risk
    findings: list[Finding]
    tests: list[str]
    next_action: Action


class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ModelResponse(TypedDict):
    text: str
    model: str
    usage: ModelUsage


class ScoreResult(TypedDict):
    score: float
    passed: bool
    matched: NotRequired[list[str]]
    missing: NotRequired[list[str]]
    false_positives: NotRequired[int]
    error: NotRequired[str]


class ModelClient(Protocol):
    calls: int

    def generate(
        self,
        *,
        model: str,
        messages: list[Message],
        max_output_tokens: int = 1200,
        compression: str = "none",
        compression_rate: float | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> ModelResponse: ...
