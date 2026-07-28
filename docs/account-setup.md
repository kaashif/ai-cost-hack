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

Go to [condense.chat](https://condense.chat/) and follow the instructions on the website.

## Safety check

```bash
git check-ignore .env
uv run costhack preflight
```

If a key is ever committed, revoke it immediately. Removing it from the newest commit is
not enough.
