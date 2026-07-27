"""Starter strategy.

Replace this with your own routing, compression, rules, or metered model calls.
"""

from __future__ import annotations

from costhack.schema import Action, Case, Finding, ModelClient, Review, Risk


def _section_text(case: Case) -> str:
    return "\n".join(
        f"{section.get('path', section['kind'])}\n{section['content']}"
        for section in case["context"]
    )


def _path_containing(case: Case, marker: str, fallback: str) -> str:
    for section in case["context"]:
        if marker in section["content"]:
            return section.get("path", fallback)
    return fallback


def review(case: Case, client: ModelClient) -> Review:
    text = _section_text(case)
    findings: list[Finding] = []
    tests: list[str] = []
    risk: Risk = "low"
    action: Action = "approve"

    if "delete_project" in text and "authorize_project" not in text:
        findings.append(
            {
                "category": "authorization",
                "severity": "high",
                "file": "api/delete_project.py",
                "evidence": "db.projects.get(project_id) is followed by deletion without an owner check",
                "explanation": "A caller can delete a project belonging to another tenant.",
            }
        )
        tests.append("cross-tenant deletion must return 403")
        risk = "high"
        action = "block"

    if "SET NOT NULL" in text and "UPDATE accounts" not in text:
        findings.append(
            {
                "category": "data_integrity",
                "severity": "high",
                "file": "migrations/042_account_region.sql",
                "evidence": "ALTER COLUMN region SET NOT NULL runs without a backfill",
                "explanation": "Existing rows with NULL region make the migration fail.",
            }
        )
        tests.append("run the migration against an existing row whose region is NULL")
        risk = "high"
        action = "request_changes"

    if "shell=True" in text and "request.form" in text:
        findings.append(
            {
                "category": "injection",
                "severity": "critical",
                "file": _path_containing(case, "shell=True", "preview/convert.py"),
                "evidence": "request.form input reaches subprocess.run(..., shell=True)",
                "explanation": "An attacker can inject shell syntax through the filename.",
            }
        )
        tests.append("a filename containing shell metacharacters is rejected")
        risk = "critical"
        action = "block"

    if "sk_live_" in text:
        findings.append(
            {
                "category": "privacy",
                "severity": "high",
                "file": _path_containing(case, "sk_live_", "config/payments.py"),
                "evidence": "API_KEY contains a hard-coded sk_live_ production credential",
                "explanation": "Anyone with repository access can use the production credential.",
            }
        )
        tests.append("secret scanning must reject a committed production credential")
        risk = "high"
        action = "request_changes"

    if "verify=False" in text:
        findings.append(
            {
                "category": "validation",
                "severity": "high",
                "file": _path_containing(case, "verify=False", "integrations/client.py"),
                "evidence": "requests.get is called with verify=False",
                "explanation": "The client will accept an untrusted server certificate.",
            }
        )
        tests.append("a self-signed certificate must be rejected")
        risk = "high"
        action = "request_changes"

    return {
        "risk": risk,
        "findings": findings,
        "tests": tests,
        "next_action": action,
    }
