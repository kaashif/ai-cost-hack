"""Starter strategy.

Replace this with your own routing, compression, rules, or metered model calls.
Do not branch on case IDs: hidden cases use different IDs and harder combinations.
"""

from __future__ import annotations


def _section_text(case: dict) -> str:
    return "\n".join(
        f"{section.get('path', section['kind'])}\n{section['content']}"
        for section in case["context"]
    )


def review(case: dict, client) -> dict:
    text = _section_text(case)
    findings = []
    tests = []
    risk = "low"
    action = "approve"

    if "delete_project" in text and "authorize_project" not in text:
        findings.append(
            {
                "category": "authorization",
                "severity": "high",
                "file": "api/delete_project.py",
                "evidence": "delete_project loads project_id and deletes it without an owner check",
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
        action = "block"

    return {
        "risk": risk,
        "findings": findings,
        "tests": tests,
        "next_action": action,
    }
