# Submission contract

## Entry point

The evaluator imports:

```python
from submission.strategy import review
```

The callable must have this shape:

```python
def review(case: dict, client) -> dict: ...
```

`case` is JSON-compatible and follows the public case schema. `client` is an
evaluator-owned, metered model client. Do not construct your own paid provider client.

## Model client

The stable method is:

```python
client.generate(
    model="default_routing",
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
    ],
    max_output_tokens=1200,
    compression="none",
    tags={"stage": "review"},
)
```

It returns a JSON-compatible dictionary with this stable shape:

```python
{
    "text": "model response text",
    "model": "resolved-model-name",
    "usage": {
        "input_tokens": 120,
        "output_tokens": 80,
    },
}
```

Token counts may be absent when a provider does not report them. The hidden evaluator
may restrict models, maximum calls, output tokens, or compression modes.

## Review output

```json
{
  "risk": "high",
  "findings": [
    {
      "category": "authorization",
      "severity": "high",
      "file": "api/delete_project.py",
      "evidence": "project_id is loaded without an owner check",
      "explanation": "A cross-tenant deletion is possible."
    }
  ],
  "tests": ["cross-tenant deletion must return 403"],
  "next_action": "block"
}
```

Allowed risk and severity values:

- `low`
- `medium`
- `high`
- `critical`

Allowed next actions:

- `approve`
- `request_changes`
- `block`

Finding categories used by the benchmark:

- `authorization`
- `authentication`
- `data_integrity`
- `data_loss`
- `dependency`
- `idempotency`
- `injection`
- `observability`
- `privacy`
- `race_condition`
- `reliability`
- `testing_gap`
- `validation`

Unknown categories are permitted but count as false positives unless a rubric expects
them.

## Limits

- At most 8 findings per case.
- Evidence must be grounded in supplied context.
- Model calls must go through `client`.
- The evaluator may execute strategy code without general network access.
- Invalid output receives zero quality for the case.
