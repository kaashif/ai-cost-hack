"""Typed boundary shared by submissions and evaluators."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

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


class ScoreResult(TypedDict):
    score: float
    passed: bool
    matched: NotRequired[list[str]]
    missing: NotRequired[list[str]]
    false_positives: NotRequired[int]
    error: NotRequired[str]
