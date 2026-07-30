#!/usr/bin/env python3
"""Safely intake and orchestrate judging of untrusted Cost Hack submissions."""

from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

API_BASE = "https://api-gateway.merge.dev/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
MAX_FILES = 5_000
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SCAN_BYTES = 512 * 1024
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
TEXT_EXTENSIONS = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
REJECT_EXTENSIONS = {
    ".7z",
    ".bin",
    ".class",
    ".dll",
    ".dylib",
    ".exe",
    ".gz",
    ".jar",
    ".o",
    ".pyc",
    ".so",
    ".tar",
    ".xz",
    ".zip",
}
REVIEW_PATTERNS = {
    "encoded-payload": re.compile(rb"(base64\.b64decode|codecs\.decode|marshal\.loads)"),
    "secret-pattern": re.compile(rb"(-----BEGIN [A-Z ]+PRIVATE KEY-----|sk-[A-Za-z0-9_-]{20,})"),
}


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def run_git(args: list[str], *, cwd: Path | None = None, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=text,
        timeout=60,
    )
    return result.stdout


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
        raise ValueError("only credential-free https://github.com/OWNER/REPO URLs are allowed")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise ValueError("repository URL must have exactly OWNER/REPO")
    owner, repo = parts
    return f"https://github.com/{owner}/{repo.removesuffix('.git')}.git"


def load_submissions(path: Path) -> list[dict[str, str | None]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        output: list[dict[str, str | None]] = []
        for index, row in enumerate(rows, 1):
            url = row.get("repo_url") or row.get("repository_url") or row.get("github_url")
            if not url:
                raise ValueError(f"CSV row {index} has no repo_url")
            output.append(
                {
                    "submission_id": row.get("submission_id") or f"submission-{index:03d}",
                    "repo_url": url,
                    "commit_sha": row.get("commit_sha") or row.get("sha") or None,
                }
            )
        return output
    output = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) > 2:
            raise ValueError(f"line {index}: expected URL and optional commit SHA")
        output.append(
            {
                "submission_id": f"submission-{len(output) + 1:03d}",
                "repo_url": fields[0],
                "commit_sha": fields[1] if len(fields) == 2 else None,
            }
        )
    return output


def finding(severity: str, code: str, message: str, path: str | None = None) -> dict[str, Any]:
    return {"severity": severity, "code": code, "path": path, "message": message}


def parse_tree(raw: bytes) -> Iterable[tuple[str, str, str, int | None, str]]:
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, object_id, size = metadata.decode().split()
        yield (
            mode,
            kind,
            object_id,
            None if size == "-" else int(size),
            path.decode(errors="replace"),
        )


def trusted_baseline_blobs() -> dict[str, str]:
    try:
        raw = run_git(["ls-tree", "-r", "-z", "-l", "HEAD"], cwd=PROJECT_ROOT, text=False)
    except (OSError, subprocess.SubprocessError):
        return {}
    return {path: object_id for _, _, object_id, _, path in parse_tree(raw)}


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def scan_python(content: bytes, path: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(content.decode("utf-8"))
    except (SyntaxError, UnicodeError) as exc:
        return [finding("review", "python-parse-error", f"cannot parse Python: {exc}", path)]
    findings = []
    call_groups = {
        "dynamic-execution": {"eval", "exec", "compile"},
        "process-execution": {
            "os.popen",
            "os.system",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "subprocess.Popen",
            "subprocess.run",
        },
        "raw-network": {
            "requests.delete",
            "requests.get",
            "requests.post",
            "requests.put",
            "socket.create_connection",
            "urllib.request.urlopen",
        },
        "encoded-payload": {
            "base64.b64decode",
            "codecs.decode",
            "marshal.loads",
        },
        "destructive-filesystem": {
            "os.remove",
            "os.unlink",
            "shutil.rmtree",
        },
    }
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func)
        for code, names in call_groups.items():
            if name in names and code not in seen:
                seen.add(code)
                findings.append(
                    finding("review", code, f"{name} call requires manual review", path)
                )
    return findings


def inspect_submission(
    item: dict[str, str | None], root: Path, baseline_blobs: dict[str, str]
) -> dict[str, Any]:
    submission_id = str(item["submission_id"])
    record: dict[str, Any] = {
        "submission_id": submission_id,
        "repo_url": item["repo_url"],
        "requested_commit": item["commit_sha"],
        "resolved_commit": None,
        "status": "reject",
        "findings": [],
        "file_count": 0,
        "total_bytes": 0,
    }
    try:
        repo_url = normalize_repo_url(str(item["repo_url"]))
        requested = item["commit_sha"]
        if requested and not SHA_RE.fullmatch(requested):
            raise ValueError("commit_sha must be a full 40-character Git SHA")
        record["repo_url"] = repo_url.removesuffix(".git")
        bare = root / hashlib.sha256(submission_id.encode()).hexdigest()[:16]
        bare.mkdir()
        run_git(["init", "--bare"], cwd=bare)
        run_git(["remote", "add", "origin", repo_url], cwd=bare)
        ref = requested or "HEAD"
        run_git(["fetch", "--depth=1", "--no-tags", "origin", ref], cwd=bare)
        commit = str(run_git(["rev-parse", "FETCH_HEAD^{commit}"], cwd=bare)).strip()
        record["resolved_commit"] = commit
        entries = list(
            parse_tree(run_git(["ls-tree", "-r", "-z", "-l", commit], cwd=bare, text=False))
        )
        record["file_count"] = len(entries)
        record["total_bytes"] = sum(size or 0 for _, _, _, size, _ in entries)
        if len(entries) > MAX_FILES:
            record["findings"].append(
                finding("reject", "too-many-files", f"{len(entries)} files exceeds {MAX_FILES}")
            )
        if record["total_bytes"] > MAX_TOTAL_BYTES:
            record["findings"].append(
                finding("reject", "repository-too-large", "repository exceeds 50 MiB")
            )
        for mode, kind, object_id, size, path in entries:
            suffix = Path(path).suffix.lower()
            if mode in {"120000", "160000"} or kind == "commit":
                record["findings"].append(
                    finding(
                        "reject", "indirect-content", "symlinks and submodules are forbidden", path
                    )
                )
            if size is not None and size > MAX_FILE_BYTES:
                record["findings"].append(
                    finding("reject", "file-too-large", "file exceeds 5 MiB", path)
                )
            if suffix in REJECT_EXTENSIONS:
                record["findings"].append(
                    finding("reject", "binary-or-archive", f"{suffix} files are forbidden", path)
                )
            if path == ".gitmodules":
                record["findings"].append(
                    finding("reject", "gitmodules", "submodule configuration is forbidden", path)
                )
            is_trusted_baseline = baseline_blobs.get(path) == object_id
            if path == "setup.py" and not is_trusted_baseline:
                record["findings"].append(
                    finding("review", "executable-configuration", "manual review required", path)
                )
            if (
                not is_trusted_baseline
                and size is not None
                and size <= MAX_SCAN_BYTES
                and (suffix in TEXT_EXTENSIONS or Path(path).name in {"Dockerfile", "Makefile"})
            ):
                content = run_git(["show", f"{commit}:{path}"], cwd=bare, text=False)
                if suffix == ".py":
                    record["findings"].extend(scan_python(content, path))
                    content_patterns = {"secret-pattern": REVIEW_PATTERNS["secret-pattern"]}
                else:
                    content_patterns = REVIEW_PATTERNS
                for code, pattern in content_patterns.items():
                    if pattern.search(content):
                        record["findings"].append(
                            finding("review", code, "suspicious capability requires review", path)
                        )
        severities = {entry["severity"] for entry in record["findings"]}
        record["status"] = (
            "reject" if "reject" in severities else "review" if severities else "pass"
        )
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as exc:
        record["findings"].append(finding("reject", "intake-error", str(exc)))
    return record


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
            "User-Agent": "ai-cost-hack-judge/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Merge Gateway {method} {path} failed ({exc.code}): {detail}") from exc


def provision(
    management_key: str, attempt_id: str, budget: float
) -> tuple[dict[str, Any], dict[str, Any]]:
    project = api_request(
        "POST",
        "/projects",
        management_key,
        {
            "name": f"Cost Hack {attempt_id}",
            "description": f"Isolated judging attempt {attempt_id}",
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
            raise RuntimeError("Merge Gateway did not return the one-time project key")
    except Exception:
        if key is not None and key.get("hash"):
            api_request(
                "PATCH",
                f"/keys/{key['hash']}",
                management_key,
                {"disabled": True},
            )
        api_request(
            "PATCH",
            f"/projects/{project['id']}",
            management_key,
            {"is_active": False},
        )
        raise
    return project, key


def close_attempt(management_key: str, project_id: str, key_hash: str) -> None:
    errors = []
    for path, body in (
        (f"/keys/{key_hash}", {"disabled": True}),
        (f"/projects/{project_id}", {"is_active": False}),
    ):
        try:
            api_request("PATCH", path, management_key, body)
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError("; ".join(errors))


def load_approvals(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def validate_sandbox_result(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("sandbox did not produce a result file")
    if path.stat().st_size > 1_000_000:
        raise RuntimeError("sandbox result exceeded 1 MB")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("sandbox result must be a JSON object")
    required_types = {
        "eligible": bool,
        "quality_score": (int, float),
        "case_count": int,
        "passed_case_count": int,
    }
    for field, expected in required_types.items():
        value = result.get(field)
        if isinstance(value, bool) and expected is not bool:
            raise RuntimeError(f"sandbox result {field} has the wrong type")
        if not isinstance(value, expected):
            raise RuntimeError(f"sandbox result {field} has the wrong type")
    if not 0 <= float(result["quality_score"]) <= 100:
        raise RuntimeError("sandbox result quality_score must be between 0 and 100")
    if not 0 <= result["passed_case_count"] <= result["case_count"]:
        raise RuntimeError("sandbox result case counts are inconsistent")
    return result


def command_intake(args: argparse.Namespace) -> int:
    submissions = load_submissions(args.input)
    baseline_blobs = trusted_baseline_blobs()
    with tempfile.TemporaryDirectory(prefix="costhack-intake-") as directory:
        records = [
            inspect_submission(item, Path(directory), baseline_blobs) for item in submissions
        ]
    manifest = {
        "version": 1,
        "created_at": now(),
        "source": str(args.input.resolve()),
        "submissions": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    counts = {
        status: sum(row["status"] == status for row in records)
        for status in ("pass", "review", "reject")
    }
    print(json.dumps({"output": str(args.output), "counts": counts}))
    return 1 if counts["reject"] else 0


def command_run(args: argparse.Namespace) -> int:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    approvals = load_approvals(args.approvals)
    selected = [
        row
        for row in manifest["submissions"]
        if row["status"] == "pass"
        or (row["status"] == "review" and row["submission_id"] in approvals)
    ]
    maximum = round(len(selected) * args.budget_usd, 2)
    print(
        json.dumps(
            {"attempts": len(selected), "budget_each_usd": args.budget_usd, "maximum_usd": maximum}
        )
    )
    if args.dry_run:
        return 0
    if not args.confirm_live:
        raise ValueError("live execution requires --confirm-live")
    management_key = os.environ.get("MERGE_GATEWAY_MANAGEMENT_KEY", "")
    if not management_key.startswith("mgmt_"):
        raise ValueError("MERGE_GATEWAY_MANAGEMENT_KEY must be a management key")
    if not args.private_cases.is_file():
        raise ValueError("private cases file does not exist")
    if not args.sandbox_command.is_file() or not os.access(args.sandbox_command, os.X_OK):
        raise ValueError("sandbox command must be an executable file")
    for index, row in enumerate(selected, 1):
        attempt_id = f"{row['submission_id']}-{row['resolved_commit'][:10]}-{index:03d}"
        audit: dict[str, Any] = {
            "attempt_id": attempt_id,
            "submission_id": row["submission_id"],
            "repo_url": row["repo_url"],
            "commit_sha": row["resolved_commit"],
            "started_at": now(),
            "finished_at": None,
            "status": "error",
            "sandbox_command": str(args.sandbox_command.resolve()),
            "return_code": None,
            "timed_out": False,
            "project_id": None,
            "key_hash": None,
            "budget_usd": args.budget_usd,
            "usage": None,
            "sandbox_result": None,
            "error": None,
        }
        project: dict[str, Any] | None = None
        key: dict[str, Any] | None = None
        try:
            project, key = provision(management_key, attempt_id, args.budget_usd)
            audit["project_id"] = project["id"]
            audit["key_hash"] = key["hash"]
            with tempfile.TemporaryDirectory(prefix="costhack-result-") as directory:
                output = Path(directory) / "result.json"
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "MERGE_GATEWAY_API_KEY": key["key"],
                    "MERGE_GATEWAY_PROJECT_ID": project["id"],
                    "COSTHACK_ATTEMPT_ID": attempt_id,
                }
                command = [
                    str(args.sandbox_command.resolve()),
                    "--repo-url",
                    row["repo_url"],
                    "--commit-sha",
                    row["resolved_commit"],
                    "--private-cases",
                    str(args.private_cases.resolve()),
                    "--output",
                    str(output),
                ]
                try:
                    completed = subprocess.run(
                        command,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=args.timeout_seconds,
                    )
                    audit["return_code"] = completed.returncode
                    if len(completed.stdout) > 100_000 or len(completed.stderr) > 100_000:
                        raise RuntimeError("sandbox output exceeded 100 KiB")
                    if completed.returncode != 0:
                        raise RuntimeError(f"sandbox exited {completed.returncode}")
                    audit["sandbox_result"] = validate_sandbox_result(output)
                    audit["status"] = "completed"
                except subprocess.TimeoutExpired:
                    audit["timed_out"] = True
                    raise RuntimeError("sandbox timed out") from None
        except Exception as exc:
            audit["error"] = str(exc)
        finally:
            if project is not None and key is not None:
                try:
                    close_attempt(management_key, project["id"], key["hash"])
                except Exception as exc:
                    audit["error"] = f"{audit['error'] or ''}; cleanup failed: {exc}".strip("; ")
                try:
                    audit["usage"] = api_request(
                        "GET", f"/projects/{project['id']}/usage", management_key
                    )
                except Exception as exc:
                    audit["error"] = f"{audit['error'] or ''}; usage failed: {exc}".strip("; ")
            audit["finished_at"] = now()
            append_jsonl(args.results, audit)
    return 0


def command_usage(args: argparse.Namespace) -> int:
    key = os.environ.get("MERGE_GATEWAY_MANAGEMENT_KEY", "")
    print(json.dumps(api_request("GET", f"/projects/{args.project_id}/usage", key), indent=2))
    return 0


def command_close(args: argparse.Namespace) -> int:
    if not args.confirm_live:
        raise ValueError("credential changes require --confirm-live")
    key = os.environ.get("MERGE_GATEWAY_MANAGEMENT_KEY", "")
    close_attempt(key, args.project_id, args.key_hash)
    print(json.dumps({"project_id": args.project_id, "key_hash": args.key_hash, "disabled": True}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    intake = sub.add_parser("intake")
    intake.add_argument("input", type=Path)
    intake.add_argument("--output", type=Path, required=True)
    intake.set_defaults(func=command_intake)

    run = sub.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--private-cases", type=Path, required=True)
    run.add_argument("--sandbox-command", type=Path, required=True)
    run.add_argument("--budget-usd", type=float, required=True)
    run.add_argument("--approvals", type=Path)
    run.add_argument("--results", type=Path, required=True)
    run.add_argument("--timeout-seconds", type=int, default=600)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--confirm-live", action="store_true")
    run.set_defaults(func=command_run)

    usage = sub.add_parser("usage")
    usage.add_argument("project_id")
    usage.set_defaults(func=command_usage)

    close = sub.add_parser("close")
    close.add_argument("project_id")
    close.add_argument("key_hash")
    close.add_argument("--confirm-live", action="store_true")
    close.set_defaults(func=command_close)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        if getattr(args, "budget_usd", 1) <= 0:
            raise ValueError("budget must be positive")
        return int(args.func(args))
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
