---
name: judge-ai-cost-hack
description: Run and publish the London AI Cost Hack leaderboard from a text or CSV list of trusted public GitHub repositories. Use when Codex needs to create one capped Merge Gateway project per entry, execute the private benchmark in Docker, collect quality and total spend, update site/leaderboard.json, or publish refreshed results to GitHub Pages.
---

# Judge AI Cost Hack

Take a repository list, run every entry once, record its Merge Gateway cost, and publish
the ranked leaderboard.

## Inputs

- `.txt`: one GitHub repository URL per line, optionally followed by a full commit SHA.
- `.csv`: `repo_url`, plus optional `team_name`, `submission_id`, and `commit_sha`.
- A private cases JSON file.
- `MERGE_GATEWAY_MANAGEMENT_KEY` with `manage_projects`, `manage_keys`, and `read_usage`.
- Docker and an explicit USD cap per entry.

## Run

Preview the number of entries and maximum spend:

```bash
uv run .codex/skills/judge-ai-cost-hack/scripts/judge.py \
  submissions.csv \
  --private-cases /secure/private_cases.json \
  --budget-usd 1.00 \
  --results results/judging.jsonl \
  --leaderboard site/leaderboard.json \
  --dry-run
```

Show the user that total and obtain confirmation immediately before spending money.
Then replace `--dry-run` with `--confirm-live`.

For each repository the command:

1. Resolves and records an immutable commit.
2. Creates a fresh hard-limited Merge Gateway project and project-scoped key.
3. Clones the commit and runs the private benchmark in a disposable, resource-limited
   Docker container.
4. Disables the key and project.
5. Reads Merge Gateway `total_spend`.
6. Appends an audit record and rewrites `site/leaderboard.json`, ranked by lowest cost
   among quality-eligible entries.

Do not rerun an entry in the same project. A rerun is a new attempt with a new project.
Never put the management key or raw project keys in results or Git.

## Publish

After checking `site/leaderboard.json`:

1. Commit and push `main`.
2. Copy `site/index.html`, `site/leaderboard.html`, `site/styles.css`,
   `site/leaderboard.js`, and `site/leaderboard.json` to the `gh-pages` worktree.
3. Commit and push `gh-pages`.
4. Wait for GitHub Pages to build and verify the live leaderboard.

The repositories are trusted event submissions, but retain Docker's non-root,
read-only, resource-limited execution so accidental breakage stays contained.
