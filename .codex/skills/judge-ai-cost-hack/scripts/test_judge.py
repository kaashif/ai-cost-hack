from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import judge


class JudgeTests(unittest.TestCase):
    def test_normalize_repository_url(self) -> None:
        self.assertEqual(
            judge.normalize_repo_url("https://github.com/example/project"),
            "https://github.com/example/project.git",
        )
        with self.assertRaises(ValueError):
            judge.normalize_repo_url("https://example.com/example/project")
        with self.assertRaises(ValueError):
            judge.normalize_repo_url("https://user:secret@github.com/example/project")

    def test_python_scan_ignores_dangerous_text_but_flags_calls(self) -> None:
        harmless = b'value = "subprocess.run(cmd)"\n'
        dangerous = b"import subprocess\nsubprocess.run(['echo', 'oops'])\n"
        self.assertEqual(judge.scan_python(harmless, "strategy.py"), [])
        self.assertEqual(
            [item["code"] for item in judge.scan_python(dangerous, "strategy.py")],
            ["process-execution"],
        )

    def test_validate_sandbox_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text(
                json.dumps(
                    {
                        "eligible": True,
                        "quality_score": 92.5,
                        "case_count": 20,
                        "passed_case_count": 20,
                        "error": None,
                    }
                )
            )
            self.assertTrue(judge.validate_sandbox_result(path)["eligible"])
            path.write_text(
                json.dumps(
                    {
                        "eligible": True,
                        "quality_score": 101,
                        "case_count": 20,
                        "passed_case_count": 20,
                    }
                )
            )
            with self.assertRaises(RuntimeError):
                judge.validate_sandbox_result(path)


if __name__ == "__main__":
    unittest.main()
