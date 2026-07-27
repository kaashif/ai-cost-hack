# London AI Cost Hack

Public challenge, quickstart, and example benchmark for
[London AI Cost Hack: Lowest Cost Wins](https://luma.com/i29x7bkv).

**Challenge:** build the cheapest AI release-gate reviewer that still catches dangerous
software changes.

The website is published with GitHub Pages:
<https://kaashif.github.io/ai-cost-hack/>

## Quickstart

```bash
git clone https://github.com/kaashif/ai-cost-hack.git
cd ai-cost-hack
uv sync
uv run costhack benchmark --public
```

Edit [submission/strategy.py](submission/strategy.py), then run the benchmark again.

Read:

1. [Quickstart](QUICKSTART.md)
1. [Challenge rules](CHALLENGE.md)
1. [Account setup](docs/account-setup.md)
1. [Submission contract](docs/submission-contract.md)

The public cases and rubrics are deliberately easy to inspect. Final ranking uses a
private, harder dataset with the same schema. Quality is a pass/fail gate; the cheapest
passing submission wins.

## Model examples

- [`examples/merge_only`](examples/merge_only/strategy.py) makes one GPT-5.5 call per
  case through Merge Gateway.
- [`examples/condense_merge`](examples/condense_merge/strategy.py) asks condense.chat to
  compress the messages before making the same GPT-5.5 call through Merge.
- [`examples/condense_proxy`](examples/condense_proxy/strategy.py) demonstrates
  Condense's OpenAI-compatible proxy with a direct upstream OpenAI key. It bypasses
  Merge, so it is illustrative and not eligible for the official benchmark.

The official Merge examples use the evaluator-owned client. All examples omit the rubric
from the model prompt and return the same typed review contract as the starter.
