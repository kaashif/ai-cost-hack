# Submission contract

## Entry point

The evaluator imports:

```python
from submission.strategy import review
```

The callable must have this shape:

```python
from costhack.schema import Case, Review


def review(case: Case) -> Review: ...
```

`case` is JSON-compatible and follows the public case schema. The organizer calls
`review(case)` directly. No model client is passed to the function.

## Model access

Create and configure your own Merge Gateway client inside the submission. Read the API
key and project ID from the environment:

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MERGE_GATEWAY_API_KEY"],
    base_url="https://api-gateway.merge.dev/v1/openai",
)
response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
    ],
    extra_body={"project_id": os.environ["MERGE_GATEWAY_PROJECT_ID"]},
)
```

The organizer records project usage before and after calling the submission. The
difference reported by Merge Gateway is the submission's measured model cost.

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
- All model inference must run through Merge Gateway.
- The evaluator allows network access to Merge Gateway while calling the submission.
- Invalid output receives zero quality for the case.

The repository includes only two complete strategies: the Python rules starter and the
GPT-5.5-through-Merge example. For condense.chat, follow the instructions on its website.
