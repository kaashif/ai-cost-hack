"""Deterministic public scoring shared with the private evaluator."""

from __future__ import annotations

from .contract import RISKS, validate_review
from .schema import Review, Rubric, ScoreResult


def _contains(text: str, needle: str) -> bool:
    return needle.casefold() in text.casefold()


def score_review(review: Review, rubric: Rubric) -> ScoreResult:
    review = validate_review(review)
    required = rubric["required_findings"]
    matched: list[str] = []
    missing: list[str] = []
    evidence_hits = 0

    for expected in required:
        candidates = [
            finding
            for finding in review["findings"]
            if finding["category"] == expected["category"] and finding["file"] == expected["file"]
        ]
        if candidates:
            matched.append(expected["id"])
            if any(_contains(item["evidence"], expected["evidence_anchor"]) for item in candidates):
                evidence_hits += 1
        else:
            missing.append(expected["id"])

    expected_pairs = {(item["category"], item["file"]) for item in required}
    false_positives = [
        finding
        for finding in review["findings"]
        if (finding["category"], finding["file"]) not in expected_pairs
    ]
    required_tests = rubric.get("required_test_terms", [])
    tests_text = "\n".join(review["tests"])
    test_hits = sum(_contains(tests_text, term) for term in required_tests)

    recall = len(matched) / max(1, len(required))
    evidence = evidence_hits / max(1, len(required))
    test_score = test_hits / max(1, len(required_tests))
    expected_risk = RISKS.index(rubric["risk"])
    actual_risk = RISKS.index(review["risk"])
    risk_score = (
        1.0 if actual_risk == expected_risk else 0.5 if actual_risk > expected_risk else 0.0
    )
    action_score = 1.0 if review["next_action"] == rubric["next_action"] else 0.0

    points = (
        recall * 50
        + evidence * 15
        + test_score * 15
        + risk_score * 10
        + action_score * 10
        - len(false_positives) * 5
    )
    points = max(0.0, min(100.0, points))
    must_find = set(rubric.get("must_find", []))
    passed = points >= rubric.get("pass_score", 80) and not (must_find & set(missing))
    return {
        "score": round(points, 1),
        "passed": passed,
        "matched": matched,
        "missing": missing,
        "false_positives": len(false_positives),
    }
