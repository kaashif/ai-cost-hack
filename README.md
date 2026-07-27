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

## Examples

- [`submission/strategy.py`](submission/strategy.py) is the zero-cost Python rules
  baseline. It catches five of ten public cases.
- [`examples/merge_only/strategy.py`](examples/merge_only/strategy.py) makes one GPT-5.5
  call per case through Merge Gateway.

Both use the evaluator-owned interface and return the same typed review contract.

After establishing a passing strategy, consider condense.chat for long, noisy cases.
Compare the same prompt and GPT-5.5 model with and without compression, then use Merge's
per-key usage as the authoritative cost. Compression is most promising when history is
large; it may add latency without helping short cases. The event needs Condense Rewrite
API access so compressed messages can still be sent through Merge.
