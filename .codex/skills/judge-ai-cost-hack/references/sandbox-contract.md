# Trusted sandbox adapter contract

The judge invokes the adapter as:

```text
ADAPTER --repo-url URL --commit-sha SHA --private-cases PATH --output PATH
```

It supplies these environment variables:

- `MERGE_GATEWAY_API_KEY`: one-time project-scoped model key
- `MERGE_GATEWAY_PROJECT_ID`: project UUID
- `COSTHACK_ATTEMPT_ID`: immutable attempt identifier

The adapter must write one JSON object to `--output`:

```json
{
  "eligible": true,
  "quality_score": 91.5,
  "case_count": 20,
  "passed_case_count": 20,
  "error": null
}
```

## Mandatory isolation

- Use a disposable VM or microVM boundary suitable for hostile code. A plain host
  subprocess is forbidden.
- Run as non-root with no privileged capabilities, host PID/IPC namespace, Docker
  socket, SSH agent, cloud metadata, or writable host mounts.
- Mount only the immutable submission snapshot and private cases. Keep private cases
  read-only and prevent model prompts or logs from exfiltrating them.
- Enforce CPU, memory, process, disk, output, and wall-clock limits.
- Allow outbound TCP only to Merge Gateway through a controlled egress proxy. Block DNS
  and all other destinations. Do not treat a normal Docker bridge as restricted egress.
- Inject only the project-scoped model key. Never inject the management key or unrelated
  organizer secrets.
- Capture bounded stdout/stderr and destroy the sandbox after each attempt.
- Do not install dependencies outside the sandbox. Treat package build hooks as code
  execution.

The operator must inspect and approve the adapter implementation before `--confirm-live`.
