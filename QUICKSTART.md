# Quickstart

## 1. Fork and install the starter

You need Git, Python 3.11 or newer, and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

First [fork the starter repository](https://github.com/kaashif/ai-cost-hack/fork) on
GitHub and keep your fork public. Then replace `YOUR-USERNAME` below with your GitHub
username and clone your fork:

```bash
git clone https://github.com/YOUR-USERNAME/ai-cost-hack.git
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

Edit `submission/strategy.py`. Your function receives one normalized release-review
case. The organizer does not pass it a model client.

It returns a structured review:

```python
def review(case):
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

You may use deterministic rules, call Merge Gateway directly, or combine both. Read your
Merge Gateway credentials from the environment. The organizer calls your function and
then uses the cost recorded in Merge Gateway.

Two complete examples are included:

- `submission/strategy.py`: local Python rules, 50% public quality, zero model calls.
- `examples/merge_only/strategy.py`: one GPT-5.5 call per case through Merge Gateway.

To start from GPT-5.5:

```bash
cp examples/merge_only/strategy.py submission/strategy.py
```

Once quality is reliable, try condense.chat on long or noisy inputs. Keep GPT-5.5 and the
prompt fixed and compare compressed and uncompressed runs. Go to
[condense.chat](https://condense.chat/) and follow the instructions on the website.

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
Submit the repository URL through the
[submission form](https://forms.gle/WFibQgZeckAAnwMFA) before the cutoff.
