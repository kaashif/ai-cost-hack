# Sponsor account setup

Event-issued credentials override these instructions. Never commit a key to your public
submission.

## Merge Gateway

1. Open [Merge Gateway signup](https://gateway.merge.dev/signup).

1. Complete the offered sign-up and verification flow.

1. If invited to the event organization, accept the invitation and switch to it.

1. Open [Settings → API keys](https://gateway.merge.dev/settings/api-keys).

1. Create or copy a regular model-calling key beginning with `mg_`.

1. Do not use an `mgmt_` management key; it cannot call models.

1. Put the key and event project ID in `.env`:

   ```dotenv
   MERGE_GATEWAY_API_KEY=mg_replace_me
   MERGE_GATEWAY_PROJECT_ID=event-team-id
   ```

1. Load and verify without spending on inference:

   ```bash
   set -a
   source .env
   set +a
   curl -sS -o /dev/null -w '%{http_code}\n' \
     https://api-gateway.merge.dev/v1/models \
     -H "Authorization: Bearer $MERGE_GATEWAY_API_KEY"
   ```

Expected result: `200`.

## condense.chat

Start at [condense.chat](https://condense.chat/). There are two supported options, and
you may use either or both.

### Coding agents

Follow the [agent setup instructions](https://condense.chat/docs/), then run Codex or
Claude Code through the `dense` CLI:

```bash
dense codex
dense claude
```

The agent keeps its normal authentication while Condense proxies its requests.

### Proxy API

For direct model calls, point an OpenAI-compatible client at the Condense proxy. Supply
both your upstream provider key and your Condense token:

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://api.condense.chat/openai/v1",
    default_headers={
        "X-Condense-Auth-Token": os.environ["CONDENSE_AUTH_TOKEN"],
    },
)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Review this change."}],
)
```

The standard OpenAI request methods continue to work. Anthropic users can follow the
equivalent example in the [Condense quickstart](https://condense.chat/docs/quickstart/).

Proxy calls use the upstream provider account and do not automatically appear in Merge
Gateway. Only model cost recorded by Merge Gateway is included in the hackathon score.

## Safety check

```bash
git check-ignore .env
uv run costhack preflight
```

If a key is ever committed, revoke it immediately. Removing it from the newest commit is
not enough.
