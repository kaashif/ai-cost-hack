#!/usr/bin/env python3
"""Run trusted Cost Hack repositories and publish a cost leaderboard."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api-gateway.merge.dev/v1"
SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PRIVATE_ROOT = PROJECT_ROOT.parent / "ai-cost-hackathon-content"
CONTAINER_IMAGE = "ghcr.io/astral-sh/uv:python3.13-bookworm-slim"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def normalize_repo_url(value: str) -> str:
    raw = value.strip()
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.removeprefix("git@github.com:")
    parsed = urllib.parse.urlsplit(raw)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("expected a credential-free https://github.com/OWNER/REPO URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise ValueError("repository URL must contain exactly OWNER/REPO")
    owner, repo = parts
    return f"https://github.com/{owner}/{repo.removesuffix('.git')}"


def load_entries(path: Path) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        for index, row in enumerate(rows, 1):
            repo = row.get("repo_url") or row.get("repository_url") or row.get("github_url")
            if not repo:
                raise ValueError(f"CSV row {index} has no repo_url")
            normalized = normalize_repo_url(repo)
            entries.append(
                {
                    "submission_id": row.get("submission_id") or f"submission-{index:03d}",
                    "team_name": row.get("team_name") or normalized.rsplit("/", 1)[-1],
                    "repo_url": normalized,
                    "commit_sha": row.get("commit_sha") or row.get("sha") or None,
                }
            )
        return entries
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) > 2:
            raise ValueError(f"line {line_number}: expected URL and optional commit SHA")
        normalized = normalize_repo_url(fields[0])
        entries.append(
            {
                "submission_id": f"submission-{len(entries) + 1:03d}",
                "team_name": normalized.rsplit("/", 1)[-1],
                "repo_url": normalized,
                "commit_sha": fields[1] if len(fields) == 2 else None,
            }
        )
    if not entries:
        raise ValueError("repository list is empty")
    return entries


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def clone_entry(entry: dict[str, str | None], destination: Path) -> str:
    requested = entry["commit_sha"]
    if requested and not SHA_RE.fullmatch(requested):
        raise ValueError("commit_sha must be a full 40-character SHA")
    run_command(["git", "init", "--quiet", str(destination)])
    run_command(["git", "-C", str(destination), "remote", "add", "origin", str(entry["repo_url"])])
    run_command(
        [
            "git",
            "-C",
            str(destination),
            "fetch",
            "--quiet",
            "--depth=1",
            "--no-tags",
            "origin",
            requested or "HEAD",
        ]
    )
    commit = run_command(
        ["git", "-C", str(destination), "rev-parse", "FETCH_HEAD^{commit}"]
    ).stdout.strip()
    run_command(["git", "-C", str(destination), "checkout", "--quiet", "--detach", commit])
    return commit


def api_request(
    method: str,
    path: str,
    management_key: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
            "User-Agent": "ai-cost-hack-judge/2",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Merge Gateway {method} {path} failed ({exc.code}): {detail}") from exc


def provision_attempt(
    management_key: str, attempt_id: str, budget: float
) -> tuple[dict[str, Any], dict[str, Any]]:
    project = api_request(
        "POST",
        "/projects",
        management_key,
        {
            "name": f"Cost Hack {attempt_id}",
            "description": f"Leaderboard attempt {attempt_id}",
            "budget_config": {
                "amount": budget,
                "period": "daily",
                "enforcement_mode": "hard_limit",
                "alert_thresholds": [80, 90],
            },
        },
    )
    key: dict[str, Any] | None = None
    try:
        key = api_request(
            "POST",
            "/keys",
            management_key,
            {
                "name": f"cost-hack-{attempt_id}",
                "project_id": project["id"],
                "limit": budget,
                "limit_reset": "daily",
            },
        )
        if "key" not in key or "hash" not in key:
            raise RuntimeError("Merge Gateway did not return a project key")
        return project, key
    except Exception:
        if key and key.get("hash"):
            api_request("PATCH", f"/keys/{key['hash']}", management_key, {"disabled": True})
        api_request("PATCH", f"/projects/{project['id']}", management_key, {"is_active": False})
        raise


def close_attempt(management_key: str, project_id: str, key_hash: str) -> list[str]:
    errors = []
    for path, body in (
        (f"/keys/{key_hash}", {"disabled": True}),
        (f"/projects/{project_id}", {"is_active": False}),
    ):
        try:
            api_request("PATCH", path, management_key, body)
        except Exception as exc:
            errors.append(str(exc))
    return errors


def run_container(
    repo: Path,
    private_cases: Path,
    api_key: str,
    project_id: str,
    judge_api_key: str,
    judge_project_id: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    evaluator = SKILL_ROOT / "scripts" / "container_evaluator.py"
    trusted_src = PROJECT_ROOT / "src"
    trusted_private_src = PRIVATE_ROOT / "src"
    public_cases = PROJECT_ROOT / "data" / "public_cases.json"
    private_gold = PRIVATE_ROOT / "hidden" / "gold_reviews.json"
    command = [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=65532:65532",
        "--pids-limit=256",
        "--memory=2g",
        "--cpus=2",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=1g,mode=1777",
        "--tmpfs=/work:rw,nosuid,size=1g,mode=1777",
        "--env",
        "MERGE_GATEWAY_API_KEY",
        "--env",
        "MERGE_GATEWAY_PROJECT_ID",
        "--env",
        "MERGE_JUDGE_API_KEY",
        "--env",
        "MERGE_JUDGE_PROJECT_ID",
        "--env",
        "UV_PROJECT_ENVIRONMENT=/tmp/venv",
        "--env",
        "UV_CACHE_DIR=/tmp/uv-cache",
        "--env",
        "HOME=/tmp/home",
        "--volume",
        f"{repo.resolve()}:/submission:ro",
        "--volume",
        f"{private_cases.resolve()}:/private_cases.json:ro",
        "--volume",
        f"{private_gold.resolve()}:/private_gold.json:ro",
        "--volume",
        f"{public_cases.resolve()}:/public_cases.json:ro",
        "--volume",
        f"{evaluator.resolve()}:/judge/container_evaluator.py:ro",
        "--volume",
        f"{trusted_src.resolve()}:/judge/src:ro",
        "--volume",
        f"{trusted_private_src.resolve()}:/judge/private_src:ro",
        CONTAINER_IMAGE,
        "sh",
        "-lc",
        (
            "cp -a /submission /work/repo && cd /work/repo && "
            "uv sync --quiet && "
            "/tmp/venv/bin/python /judge/container_evaluator.py"
        ),
    ]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "MERGE_GATEWAY_API_KEY": api_key,
        "MERGE_GATEWAY_PROJECT_ID": project_id,
        "MERGE_JUDGE_API_KEY": judge_api_key,
        "MERGE_JUDGE_PROJECT_ID": judge_project_id,
    }
    try:
        completed = run_command(command, env=env, timeout=timeout_seconds)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "")[-2_000:]
        raise RuntimeError(f"submission container failed: {detail}") from exc
    result_lines = [
        line.removeprefix("COSTHACK_RESULT=")
        for line in completed.stdout.splitlines()
        if line.startswith("COSTHACK_RESULT=")
    ]
    if len(result_lines) != 1:
        raise RuntimeError("submission did not produce exactly one benchmark result")
    result = json.loads(result_lines[0])
    if not isinstance(result, dict):
        raise RuntimeError("benchmark result is not an object")
    return result


def stable_usage(management_key: str, project_id: str) -> dict[str, Any]:
    time.sleep(2)
    return api_request("GET", f"/projects/{project_id}/usage", management_key)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def load_audit(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_leaderboard(results_path: Path, output: Path) -> None:
    latest: dict[str, dict[str, Any]] = {}
    for record in load_audit(results_path):
        if record.get("status") == "completed":
            latest[record["submission_id"]] = record
    eligible = [
        record
        for record in latest.values()
        if record.get("benchmark", {}).get("eligible") is True
        and isinstance(record.get("usage", {}).get("total_spend"), (int, float))
    ]
    eligible.sort(
        key=lambda record: (
            float(record["usage"]["total_spend"]),
            -float(record["benchmark"]["private"]["quality_score"]),
            record["team_name"].casefold(),
        )
    )
    entries = [
        {
            "rank": rank,
            "team_name": record["team_name"],
            "repo_url": record["repo_url"],
            "commit_sha": record["commit_sha"],
            "public_score": record["benchmark"]["public"]["quality_score"],
            "public_passed_cases": record["benchmark"]["public"]["passed_case_count"],
            "public_total_cases": record["benchmark"]["public"]["case_count"],
            "private_score": record["benchmark"]["private"]["quality_score"],
            "private_passed_cases": record["benchmark"]["private"]["passed_case_count"],
            "private_total_cases": record["benchmark"]["private"]["case_count"],
            "cost_usd": record["usage"]["total_spend"],
        }
        for rank, record in enumerate(eligible, 1)
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"generated_at": now(), "entries": entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submissions", type=Path)
    parser.add_argument("--private-cases", type=Path, required=True)
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument("--judge-budget-usd", type=float, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--leaderboard", type=Path, default=PROJECT_ROOT / "site/leaderboard.json")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm-live", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        entries = load_entries(args.submissions)
        if args.budget_usd <= 0 or args.judge_budget_usd <= 0:
            raise ValueError("participant and judge budgets must be positive")
        maximum = round(len(entries) * (args.budget_usd + args.judge_budget_usd), 2)
        print(
            json.dumps(
                {
                    "entries": len(entries),
                    "participant_budget_each_usd": args.budget_usd,
                    "judge_budget_each_usd": args.judge_budget_usd,
                    "maximum_usd": maximum,
                }
            )
        )
        if args.dry_run:
            return 0
        required_inputs = [
            args.private_cases,
            PRIVATE_ROOT / "hidden" / "gold_reviews.json",
            PRIVATE_ROOT / "src" / "patchguard_private",
            PROJECT_ROOT / "data" / "public_cases.json",
        ]
        if any(not path.exists() for path in required_inputs):
            raise ValueError("one or more public/private benchmark inputs do not exist")
        run_command(["docker", "info", "--format", "{{.ServerVersion}}"])
        management_key = os.environ.get("MERGE_GATEWAY_MANAGEMENT_KEY", "")
        if not management_key.startswith("mgmt_"):
            raise ValueError("MERGE_GATEWAY_MANAGEMENT_KEY must start with mgmt_")
        for index, entry in enumerate(entries, 1):
            with tempfile.TemporaryDirectory(prefix="costhack-run-") as directory:
                commit = clone_entry(entry, Path(directory) / "repo")
                attempt_id = f"{entry['submission_id']}-{commit[:10]}-{index:03d}"
                audit: dict[str, Any] = {
                    "attempt_id": attempt_id,
                    "submission_id": entry["submission_id"],
                    "team_name": entry["team_name"],
                    "repo_url": entry["repo_url"],
                    "commit_sha": commit,
                    "budget_usd": args.budget_usd,
                    "judge_budget_usd": args.judge_budget_usd,
                    "started_at": now(),
                    "finished_at": None,
                    "status": "error",
                    "project_id": None,
                    "key_hash": None,
                    "judge_project_id": None,
                    "judge_key_hash": None,
                    "benchmark": None,
                    "usage": None,
                    "judge_usage": None,
                    "error": None,
                }
                project: dict[str, Any] | None = None
                key: dict[str, Any] | None = None
                judge_project: dict[str, Any] | None = None
                judge_key: dict[str, Any] | None = None
                try:
                    project, key = provision_attempt(management_key, attempt_id, args.budget_usd)
                    audit["project_id"] = project["id"]
                    audit["key_hash"] = key["hash"]
                    judge_project, judge_key = provision_attempt(
                        management_key,
                        f"{attempt_id}-quality-judge",
                        args.judge_budget_usd,
                    )
                    audit["judge_project_id"] = judge_project["id"]
                    audit["judge_key_hash"] = judge_key["hash"]
                    audit["benchmark"] = run_container(
                        Path(directory) / "repo",
                        args.private_cases,
                        key["key"],
                        project["id"],
                        judge_key["key"],
                        judge_project["id"],
                        args.timeout_seconds,
                    )
                    audit["status"] = "completed"
                except Exception as exc:
                    audit["error"] = str(exc)
                finally:
                    if project is not None and key is not None:
                        cleanup_errors = close_attempt(management_key, project["id"], key["hash"])
                        if cleanup_errors:
                            audit["error"] = "; ".join(
                                [value for value in [audit["error"], *cleanup_errors] if value]
                            )
                        try:
                            audit["usage"] = stable_usage(management_key, project["id"])
                        except Exception as exc:
                            audit["error"] = "; ".join(
                                [value for value in [audit["error"], str(exc)] if value]
                            )
                    if judge_project is not None and judge_key is not None:
                        cleanup_errors = close_attempt(
                            management_key, judge_project["id"], judge_key["hash"]
                        )
                        if cleanup_errors:
                            audit["error"] = "; ".join(
                                [value for value in [audit["error"], *cleanup_errors] if value]
                            )
                        try:
                            audit["judge_usage"] = stable_usage(management_key, judge_project["id"])
                        except Exception as exc:
                            audit["error"] = "; ".join(
                                [value for value in [audit["error"], str(exc)] if value]
                            )
                    audit["finished_at"] = now()
                    append_jsonl(args.results, audit)
                    write_leaderboard(args.results, args.leaderboard)
        print(json.dumps({"leaderboard": str(args.leaderboard), "results": str(args.results)}))
        return 0
    except (
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
