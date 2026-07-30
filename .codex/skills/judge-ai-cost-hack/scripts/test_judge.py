from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import judge


class JudgeTests(unittest.TestCase):
    def test_load_text_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repos.txt"
            path.write_text("https://github.com/example/project\n", encoding="utf-8")
            entries = judge.load_entries(path)
        self.assertEqual(entries[0]["team_name"], "project")
        self.assertEqual(entries[0]["repo_url"], "https://github.com/example/project")

    def test_rejects_non_github_url(self) -> None:
        with self.assertRaises(ValueError):
            judge.normalize_repo_url("https://example.com/example/project")

    def test_writes_ranked_leaderboard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.jsonl"
            leaderboard = Path(directory) / "leaderboard.json"
            records = [
                {
                    "status": "completed",
                    "submission_id": "two",
                    "team_name": "Team Two",
                    "repo_url": "https://github.com/example/two",
                    "commit_sha": "b" * 40,
                    "benchmark": {"eligible": True, "quality_score": 90},
                    "usage": {"total_spend": 0.2},
                },
                {
                    "status": "completed",
                    "submission_id": "one",
                    "team_name": "Team One",
                    "repo_url": "https://github.com/example/one",
                    "commit_sha": "a" * 40,
                    "benchmark": {"eligible": True, "quality_score": 91},
                    "usage": {"total_spend": 0.1},
                },
            ]
            results.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            judge.write_leaderboard(results, leaderboard)
            output = json.loads(leaderboard.read_text())
        self.assertEqual(
            [entry["team_name"] for entry in output["entries"]], ["Team One", "Team Two"]
        )
        self.assertEqual([entry["rank"] for entry in output["entries"]], [1, 2])


if __name__ == "__main__":
    unittest.main()
