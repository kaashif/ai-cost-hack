"""Small public CLI for inspecting and running public examples."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

from .contract import OfflineModelClient, validate_review
from .scoring import score_review

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DATA = ROOT / "data" / "public_cases.json"


def _load_cases() -> list[dict]:
    return json.loads(PUBLIC_DATA.read_text())


def _load_strategy():
    path = ROOT / "submission" / "strategy.py"
    spec = importlib.util.spec_from_file_location("submission.strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load strategy from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def benchmark() -> int:
    strategy = _load_strategy()
    client = OfflineModelClient()
    rows = []
    for case in _load_cases():
        try:
            review = validate_review(strategy.review(case, client))
            result = score_review(review, case["rubric"])
        except Exception as exc:  # noqa: BLE001 - participant errors are isolated per case
            result = {"score": 0.0, "passed": False, "missing": [], "error": str(exc)}
        rows.append((case["id"], result))

    print("PATCHGUARD PUBLIC BENCHMARK")
    print("=" * 72)
    for case_id, result in rows:
        status = "PASS" if result["passed"] else "FAIL"
        detail = f" missing={','.join(result.get('missing', []))}" if result.get("missing") else ""
        if result.get("error"):
            detail += f" error={result['error']}"
        print(f"{status:4}  {result['score']:5.1f}  {case_id}{detail}")
    mean = sum(row[1]["score"] for row in rows) / max(1, len(rows))
    passed = all(row[1]["passed"] for row in rows)
    print("-" * 72)
    print(
        f"{'ELIGIBLE' if passed else 'NOT ELIGIBLE'}  quality={mean:.1f}  model_calls={client.calls}"
    )
    print("Public cost is $0.00 because the starter strategy is local.")
    return 0 if passed else 1


def inspect_case(case_id: str) -> int:
    case = next((item for item in _load_cases() if item["id"] == case_id), None)
    if case is None:
        print(f"unknown case: {case_id}", file=sys.stderr)
        return 2
    print(json.dumps(case, indent=2))
    return 0


def preflight() -> int:
    problems = []
    env_path = ROOT / ".env"
    if env_path.exists() and os.system("git check-ignore -q .env") != 0:
        problems.append(".env exists but is not ignored by Git")
    strategy = ROOT / "submission" / "strategy.py"
    if not strategy.exists():
        problems.append("submission/strategy.py is missing")
    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    print("PASS submission entry point")
    print("PASS local secret-file policy")
    print("INFO sponsor credentials are optional for the offline starter")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="costhack")
    sub = parser.add_subparsers(dest="command", required=True)
    benchmark_parser = sub.add_parser("benchmark")
    benchmark_parser.add_argument("--public", action="store_true")
    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("case_id")
    sub.add_parser("preflight")
    args = parser.parse_args()
    if args.command == "benchmark":
        raise SystemExit(benchmark())
    if args.command == "inspect":
        raise SystemExit(inspect_case(args.case_id))
    raise SystemExit(preflight())
