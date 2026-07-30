# Output schemas

## Intake manifest

`intake` writes one JSON object with `version`, `created_at`, `source`, and `submissions`.
Each submission includes:

- `submission_id`
- `repo_url`
- `requested_commit`
- `resolved_commit`
- `status`: `pass`, `review`, or `reject`
- `findings`: objects with `severity`, `code`, `path`, and `message`
- `file_count`
- `total_bytes`

## Judging JSONL

`run` appends one object per attempt:

- identity: `attempt_id`, `submission_id`, `repo_url`, `commit_sha`
- lifecycle: `started_at`, `finished_at`, `status`
- isolation: `sandbox_command`, `return_code`, `timed_out`
- Merge: `project_id`, `key_hash`, `budget_usd`, `usage`
- scoring: `sandbox_result`
- failure detail: `error`

Raw API keys must never appear in intake, logs, results, or error messages.
