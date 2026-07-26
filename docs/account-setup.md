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

The recommended path is the official dense CLI.

1. Install it:

   ```bash
   curl -fsSL https://cli.condense.chat/unix | sh
   ```

1. Run:

   ```bash
   dense login
   ```

1. Complete the browser device flow. Choose **Sign up** if you do not yet have an
   account.

1. Verify:

   ```bash
   dense status
   dense doctor
   ```

For direct API access instead, sign up at
[login.condense.chat](https://login.condense.chat/sign-up?return=https%3A%2F%2Fhelm.condense.chat),
claim an `ak_…` key in the dashboard, and put it in `.env`:

```dotenv
CONDENSE_AUTH_TOKEN=ak_replace_me
```

The condense key travels in `X-Condense-Auth-Token`. When condense proxies directly to
OpenAI or Anthropic, an upstream provider key is also required. Follow the starter's
event configuration rather than inventing a chain of credentials.

## Safety check

```bash
git check-ignore .env
uv run costhack preflight
```

If a key is ever committed, revoke it immediately. Removing it from the newest commit is
not enough.
