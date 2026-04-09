import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.services import settings_manager


class SettingsManagerTests(unittest.TestCase):
    def test_get_settings_payload_reads_expected_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_path = root / "job_search.yaml"
            settings_path = root / "settings.yaml"

            job_path.write_text(
                yaml.safe_dump(
                    {
                        "target_roles": ["Senior Data Scientist"],
                        "locations": ["Remote"],
                        "filters": {
                            "include_keywords": ["ml"],
                            "exclude_keywords": ["sales"],
                        },
                        "sources": {
                            "remoteok": {"enabled": True, "url": "x"},
                            "himalayas": {"enabled": False, "url": "y"},
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            settings_path.write_text(
                yaml.safe_dump(
                    {
                        "jobs": {"daily_limit": 12},
                        "schedule": {
                            "linkedin_post_window_start": 8,
                            "linkedin_post_window_end": 10,
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            with patch.object(settings_manager, "JOB_SEARCH_PATH", job_path), patch.object(
                settings_manager, "SETTINGS_PATH", settings_path
            ), patch("src.services.settings_manager.get_environment_status", return_value={}):
                payload = settings_manager.get_settings_payload()

            self.assertEqual(payload["daily_job_limit"], 12)
            self.assertIn("remoteok", payload["job_sources"])
            self.assertEqual(payload["posting_time_window"]["start_hour"], 8)

    def test_update_settings_payload_persists_selected_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_path = root / "job_search.yaml"
            settings_path = root / "settings.yaml"

            job_path.write_text(
                yaml.safe_dump(
                    {
                        "target_roles": ["old"],
                        "locations": ["old"],
                        "filters": {
                            "include_keywords": ["old"],
                            "exclude_keywords": ["old"],
                        },
                        "sources": {"remoteok": {"enabled": True, "url": "x"}},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            settings_path.write_text(
                yaml.safe_dump(
                    {
                        "jobs": {"daily_limit": 10},
                        "schedule": {
                            "linkedin_post_window_start": 8,
                            "linkedin_post_window_end": 11,
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            update = {
                "target_roles": ["new role"],
                "locations": ["new location"],
                "include_keywords": ["python"],
                "exclude_keywords": ["sales"],
                "daily_job_limit": 20,
                "posting_time_window": {"start_hour": 9, "end_hour": 12},
                "job_sources": {"remoteok": False},
            }

            with patch.object(settings_manager, "JOB_SEARCH_PATH", job_path), patch.object(
                settings_manager, "SETTINGS_PATH", settings_path
            ), patch("src.services.settings_manager.get_environment_status", return_value={}):
                updated = settings_manager.update_settings_payload(update)

            self.assertEqual(updated["daily_job_limit"], 20)
            self.assertEqual(updated["job_sources"]["remoteok"], False)

            saved_job = yaml.safe_load(job_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_job["target_roles"], ["new role"])


    def test_get_settings_payload_does_not_return_secret_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            job_path = root / "job_search.yaml"
            settings_path = root / "settings.yaml"
            job_path.write_text("{}", encoding="utf-8")
            settings_path.write_text("{}", encoding="utf-8")

            with patch.object(settings_manager, "JOB_SEARCH_PATH", job_path), patch.object(
                settings_manager, "SETTINGS_PATH", settings_path
            ), patch(
                "src.services.settings_manager.get_environment_status",
                return_value={
                    "ANTHROPIC_API_KEY": {
                        "set": True,
                        "required": True,
                        "description": "Required for Claude AI.",
                        "value": "sk-ant-secret",
                    }
                },
            ):
                payload = settings_manager.get_settings_payload()

            self.assertIn("ANTHROPIC_API_KEY", payload["secret_status"])
            self.assertNotIn("value", payload["secret_status"]["ANTHROPIC_API_KEY"])


if __name__ == "__main__":
    unittest.main()
