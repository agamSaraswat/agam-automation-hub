import tempfile
import unittest
from pathlib import Path

from src.services import run_history


class RunHistoryTests(unittest.TestCase):
    def test_append_and_read_recent_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.jsonl"
            original_path = run_history.RUN_HISTORY_PATH
            run_history.RUN_HISTORY_PATH = history_path
            try:
                run_history.append_run_record(
                    task_type="jobs",
                    start_time="2026-04-09T10:00:00+00:00",
                    end_time="2026-04-09T10:00:05+00:00",
                    status="success",
                    summary="Scraped 2 jobs",
                )
                rows = run_history.get_recent_runs(limit=10)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["task_type"], "jobs")
            finally:
                run_history.RUN_HISTORY_PATH = original_path

    def test_run_with_history_records_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.jsonl"
            original_path = run_history.RUN_HISTORY_PATH
            run_history.RUN_HISTORY_PATH = history_path
            try:
                with self.assertRaises(RuntimeError):
                    run_history.run_with_history(
                        "gmail",
                        lambda _: "ok",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                    )

                rows = run_history.get_recent_runs(limit=10)
                self.assertEqual(rows[0]["status"], "failed")
                self.assertIn("boom", rows[0]["error_message"])
            finally:
                run_history.RUN_HISTORY_PATH = original_path


    def test_run_history_redacts_sensitive_error_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.jsonl"
            original_path = run_history.RUN_HISTORY_PATH
            run_history.RUN_HISTORY_PATH = history_path
            try:
                run_history.append_run_record(
                    task_type="linkedin_generation",
                    start_time="2026-04-09T10:00:00+00:00",
                    end_time="2026-04-09T10:00:01+00:00",
                    status="failed",
                    summary="failed",
                    error_message="Authorization: Bearer sk-ant-secret-token-value",
                )
                row = run_history.get_recent_runs(limit=1)[0]
                self.assertNotIn("sk-ant-secret", row["error_message"])
                self.assertIn("[REDACTED]", row["error_message"])
            finally:
                run_history.RUN_HISTORY_PATH = original_path

    def test_summary_builder_failure_does_not_fail_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.jsonl"
            original_path = run_history.RUN_HISTORY_PATH
            run_history.RUN_HISTORY_PATH = history_path
            try:
                result = run_history.run_with_history(
                    "jobs",
                    lambda _: (_ for _ in ()).throw(ValueError("summary broke")),
                    lambda: {"ok": True},
                )
                self.assertEqual(result["ok"], True)
                row = run_history.get_recent_runs(limit=1)[0]
                self.assertEqual(row["status"], "success")
            finally:
                run_history.RUN_HISTORY_PATH = original_path


if __name__ == "__main__":
    unittest.main()
