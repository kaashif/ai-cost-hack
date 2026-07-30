---
name: judge-ai-cost-hack
description: Intake, security-review, and judge London AI Cost Hack repository submissions from a text or CSV list. Use when Codex must resolve immutable GitHub commits, screen untrusted submissions without executing them, provision one hard-limited Merge Gateway project and key per attempt, invoke an approved sandbox runner, collect quality and spend, or produce an auditable results file.
---

# Judge AI Cost Hack

Treat every submitted repository as hostile. Static screening reduces risk; only an
isolated sandbox makes execution acceptable.

## Required inputs

- A `.txt` file containing one public GitHub repository URL per line, or a `.csv` with
  `repo_url` and optional `submission_id` and `commit_sha` columns.
- The private cases file, kept outside every submitted repository.
- A trusted sandbox adapter satisfying `references/sandbox-contract.md`.
- For live runs, `MERGE_GATEWAY_MANAGEMENT_KEY` with `manage_projects`, `manage_keys`,
  and `read_usage` scopes.
- An explicit per-attempt USD budget.

Never accept uploaded archives, participant credentials, local filesystem paths, or
non-GitHub URLs.

## Workflow

1. Run intake before reading repository files manually:

   ```bash
   uv run .codex/skills/judge-ai-cost-hack/scripts/judge.py intake \
     submissions.csv --output results/intake.json
   ```

2. Inspect every finding in `results/intake.json`. Reject structural failures. Manually
   review every `review` result and record approved submission IDs in a newline-delimited
   approvals file. A clean static result is not proof of safety.

3. Read `references/sandbox-contract.md` and inspect the configured adapter. Do not
   continue if it permits host mounts, the Docker socket, privileged execution, arbitrary
   outbound network access, or access to the management key.

4. Dry-run the judging plan:

   ```bash
   uv run .codex/skills/judge-ai-cost-hack/scripts/judge.py run \
     results/intake.json \
     --private-cases /secure/private_cases.json \
     --sandbox-command /trusted/bin/costhack-sandbox \
     --budget-usd 1.00 \
     --approvals results/approved.txt \
     --results results/judging.jsonl \
     --dry-run
   ```

5. Show the user the exact number of attempts and maximum aggregate spend. Obtain
   confirmation immediately before the live run. Then add `--confirm-live`.

6. During a live run, create a fresh project and project-scoped key per attempt. Pass
   only the model-calling key and project ID into the sandbox. The script disables both
   in `finally`, even when the sandbox fails.

7. Read project usage after the key is disabled. Use Merge Gateway `total_spend` as the
   official cost. Preserve project IDs, key hashes, immutable commit SHAs, sandbox
   results, errors, and timestamps in the JSONL output. Never store raw keys.

8. Rank only eligible submissions. Keep failed, rejected, and timed-out attempts in the
   audit output. Do not rerun an attempt in the same project; use a new attempt ID,
   project, and key.

## Safety invariants

- Never import or execute submission code on the host.
- Never install submission dependencies on the host.
- Never expose the Merge management key to the sandbox.
- Never rely on model output or static scanning as a malware guarantee.
- Never run entries marked `review` without an explicit approvals file entry.
- Never weaken the budget, timeout, or sandbox to make a submission pass.
- Stop and disable credentials if usage exceeds the configured budget, the sandbox
  contract is violated, or results cannot be attributed to exactly one project.

## Tools

`scripts/judge.py` provides:

- `intake`: resolve commits and inspect Git trees without checkout or execution.
- `run --dry-run`: validate the judging plan without API mutation or code execution.
- `run --confirm-live`: provision, invoke the trusted adapter, disable credentials, read
  usage, and append audit records.
- `usage`: read a previously created project's spend.
- `close`: disable a project key and deactivate its project.

Read `references/results-schema.md` when consuming or transforming output.
