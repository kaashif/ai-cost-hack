"""Trusted public and private benchmark harness executed inside a submission container."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/judge/src")
sys.path.insert(1, "/judge/private_src")
sys.path.insert(2, "/work/repo")

from patchguard_private.evaluator import load_cases, load_gold_reviews
from patchguard_private.judge import SemanticJudge
from patchguard_private.scoring import score_review_with_judge

from costhack.contract import validate_review
from costhack.scoring import score_review


def load_strategy() -> Any:
    path = Path("/work/repo/submission/strategy.py")
    spec = importlib.util.spec_from_file_location("submission.strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("submission/strategy.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_public(strategy: Any) -> dict[str, Any]:
    cases = json.loads(Path("/public_cases.json").read_text())
    scores: list[float] = []
    errors: list[str] = []
    for case_with_rubric in cases:
        case = dict(case_with_rubric)
        rubric = case.pop("rubric")
        try:
            result = score_review(validate_review(strategy.review(case)), rubric)
            scores.append(float(result["score"]))
            if not result["passed"]:
                errors.append(case.get("id", "unknown"))
        except Exception as exc:
            scores.append(0.0)
            errors.append(f"{case.get('id', 'unknown')}: {exc}")
    return {
        "eligible": not errors,
        "quality_score": round(sum(scores) / max(1, len(scores)), 2),
        "case_count": len(cases),
        "passed_case_count": len(cases) - len(errors),
        "errors": errors,
    }


def evaluate_private(strategy: Any) -> dict[str, Any]:
    cases = load_cases(Path("/private_cases.json"))
    gold_reviews = load_gold_reviews(Path("/private_gold.json"))
    judge = SemanticJudge(
        api_key=os.environ["MERGE_JUDGE_API_KEY"],
        project_id=os.environ["MERGE_JUDGE_PROJECT_ID"],
        ledger_path=Path("/tmp/judge-ledger.jsonl"),
    )
    scores: list[float] = []
    errors: list[str] = []
    for case_with_rubric in cases:
        case = dict(case_with_rubric)
        rubric = case.pop("rubric")
        case_id = case.get("id", "unknown")
        try:
            participant_case = {
                "id": case["id"],
                "title": case["title"],
                "brief": case["brief"],
                "context": case["context"],
            }
            review = validate_review(strategy.review(participant_case))
            result = score_review_with_judge(
                review=review,
                rubric=rubric,
                case=case,
                expected_review=gold_reviews[case_id],
                judge=judge,
            )
            scores.append(float(result["score"]))
            if not result["passed"]:
                errors.append(case_id)
        except Exception as exc:
            scores.append(0.0)
            errors.append(f"{case_id}: {exc}")
    quality = round(sum(scores) / max(1, len(scores)), 2)
    return {
        "eligible": quality >= 85 and not errors,
        "quality_score": quality,
        "case_count": len(cases),
        "passed_case_count": len(cases) - len(errors),
        "judge_calls": judge.calls,
        "errors": errors,
    }


def main() -> None:
    strategy = load_strategy()
    public = evaluate_public(strategy)
    private = evaluate_private(strategy)
    result = {
        "eligible": private["eligible"],
        "public": public,
        "private": private,
        "judge_model": "google/gemini-3.1-flash-lite",
    }
    print(f"COSTHACK_RESULT={json.dumps(result, separators=(',', ':'))}")


if __name__ == "__main__":
    main()
