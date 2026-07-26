# Quickstart

## 1. Install the starter

You need Git, Python 3.11 or newer, and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/kaashif/ai-cost-hack.git
cd ai-cost-hack
uv sync
```

## 2. Run the public benchmark

```bash
uv run costhack benchmark --public
```

The starter strategy is local and makes no paid API calls. It intentionally catches only
five of the ten public cases, scoring 50%. Improve it before optimizing cost.

## 3. Inspect a case

```bash
uv run costhack inspect public-auth-delete
```

Public cases include their rubrics. Hidden cases do not, but use the same fields,
categories, and output contract.

## 4. Change the strategy

Edit `submission/strategy.py`. Your function receives:

- a normalized release-review case; and
- a metered model client supplied by the evaluator.

It returns a structured review:

```python
def review(case, client):
    return {
        "risk": "high",
        "findings": [
            {
                "category": "authorization",
                "severity": "high",
                "file": "api/delete_project.py",
                "evidence": "The handler loads by project_id but never checks owner_id.",
                "explanation": "A user can delete another tenant's project.",
            }
        ],
        "tests": ["Attempt deletion using a project owned by another tenant"],
        "next_action": "block",
    }
```

You may call `client.generate(...)`, use deterministic rules, or combine both. All model
calls made through the supplied client are metered. Unmetered external model calls are
not allowed.

## 5. Set up sponsor accounts

Follow [the account setup guide](docs/account-setup.md). Keep secrets in `.env`; never
commit it.

```bash
cp .env.example .env
chmod 600 .env
```

## 6. Validate before submitting

```bash
uv run costhack preflight
uv run pytest
git status --short
```

Your public repository must contain `submission/strategy.py` and an exact dependency lock.
Submit the repository URL and commit SHA before the cutoff.
