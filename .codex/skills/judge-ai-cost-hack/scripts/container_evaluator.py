"""Trusted benchmark harness executed inside the submission container."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/judge/src")
sys.path.insert(1, "/work/repo")

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


def main() -> None:
    cases = json.loads(Path("/private_cases.json").read_text())
    strategy = load_strategy()
    scores = []
    errors = []
    for case_with_rubric in cases:
        case = dict(case_with_rubric)
        rubric = case.pop("rubric")
        try:
            review = validate_review(strategy.review(case))
            result = score_review(review, rubric)
            scores.append(float(result["score"]))
            if not result["passed"]:
                errors.append(case.get("id", "unknown"))
        except Exception as exc:
            scores.append(0.0)
            errors.append(f"{case.get('id', 'unknown')}: {exc}")
    quality = sum(scores) / max(1, len(scores))
    result = {
        "eligible": not errors,
        "quality_score": round(quality, 2),
        "case_count": len(cases),
        "passed_case_count": len(cases) - len(errors),
        "errors": errors,
    }
    print(f"COSTHACK_RESULT={json.dumps(result, separators=(',', ':'))}")


if __name__ == "__main__":
    main()
