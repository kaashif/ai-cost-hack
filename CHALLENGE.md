# The challenge: PatchGuard

Build the cheapest AI release-gate reviewer that still stops dangerous software changes.

## The workflow

Each case represents a pull request about to merge. It contains a mixture of:

- the pull-request description and issue;
- changed files or focused diffs;
- repository and ownership metadata;
- CI output and test history;
- dependency or migration information;
- earlier review comments and tool output.

Your submission must produce:

- an overall risk: `low`, `medium`, `high`, or `critical`;
- zero or more evidence-backed findings;
- a minimal verification plan;
- the next action: `approve`, `request_changes`, or `block`.

## What makes the hidden set harder

The public set contains five direct defects and five multi-signal defects. Hidden cases
use longer, noisier combinations that include:

- authorization failures that only appear when cache or tenant keys are considered;
- race conditions, retry bugs, and broken idempotency;
- migrations that can corrupt or silently drop production data;
- transitive dependency risks;
- misleading green CI caused by tests that never ran;
- unsafe instructions embedded in repository content;
- long, noisy context where the relevant evidence is far apart.

The hidden set is not a trivia quiz. Every required finding is supported by evidence in
the case.

## Optimization space

You may:

- select different models for different cases;
- route through Merge Gateway;
- compress context with condense.chat;
- retrieve or select only relevant sections;
- use rules, caching, or no model at all;
- make multiple metered calls when the extra quality is worth the cost.

Suggested condense.chat experiment:

1. Build a passing GPT-5.5-through-Merge baseline.
1. Compress only long or noisy case context with condense.chat.
1. Try Condense's proxy or send rewritten messages through Merge.
1. Compare quality, latency, and recorded cost against the uncompressed run.

## Rule

Model inference must run through Merge Gateway so its cost appears in the official usage
record.

## Scoring

Scoring has two stages.

### 1. Quality gate

A review earns points for:

- catching required issue categories;
- citing the correct file and useful evidence;
- choosing an appropriate risk level;
- proposing the important verification steps;
- taking the correct release action.

False positives reduce the score. Missing a must-find critical issue fails the case.

The final quality threshold is calibrated against repeated control runs. A submission
must pass quality before its cost is considered.

### 2. Cost ranking

Among eligible submissions, the lowest Merge Gateway-measured cost wins. The organizer
records project usage before and after calling the submission on the hidden benchmark.
The difference is the submission's cost. Raw token count and costs reported by participant
code are not used.

Close results may be rerun. Published tie-breaks are:

1. higher quality;
1. lower p95 latency;
1. fewer remote model calls.

## Submission

Submit:

- your public GitHub repository URL through the
  [submission form](https://forms.gle/WFibQgZeckAAnwMFA);
- `submission/strategy.py`;
- a locked environment;
- `SUBMISSION.md` describing the approach.

The organizer runs the submitted repository against the hidden benchmark.
