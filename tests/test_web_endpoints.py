import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment dependency
    TestClient = None


@unittest.skipIf(TestClient is None, "fastapi/testclient not installed")
class WebEndpointTests(unittest.TestCase):
    def setUp(self):
        from src.web.main import app

        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("service", payload)
        self.assertIn("date", payload)

    @patch("src.web.routers.status.get_system_status")
    def test_status_endpoint(self, mock_status):
        mock_status.return_value = {
            "date": "2026-04-09",
            "environment": {
                "ANTHROPIC_API_KEY": {
                    "set": False,
                    "required": True,
                    "description": "Required for Claude AI.",
                }
            },
            "jobs": {
                "total_jobs": 0,
                "today_queued": 0,
                "by_status": {},
            },
            "linkedin": {
                "status": "Not generated",
                "today": "2026-04-09",
                "queue_file_exists": False,
                "posted_file_exists": False,
                "token_set_date": None,
                "token_age_days": None,
                "token_warning": None,
            },
        }

        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["date"], "2026-04-09")
        self.assertIn("environment", payload)
        self.assertIn("jobs", payload)
        self.assertIn("linkedin", payload)

    @patch("src.web.routers.linkedin.get_draft_snapshot")
    def test_linkedin_draft_endpoint(self, mock_get_draft):
        mock_get_draft.return_value = {
            "today": "2026-04-09",
            "exists": True,
            "content": "Draft content",
            "metadata": {"status": "draft"},
            "status": "draft",
            "publish_supported": False,
        }

        response = self.client.get("/api/linkedin/draft")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["exists"])
        self.assertEqual(payload["status"], "draft")

    @patch("src.web.routers.linkedin.publish_approved_draft")
    def test_linkedin_publish_endpoint(self, mock_publish):
        mock_publish.return_value = "Published (ID: abc123)"

        response = self.client.post("/api/linkedin/draft/publish", json={"confirm_publish": True})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["published"])
        self.assertIn("Published", payload["message"])

    @patch("src.web.routers.linkedin.publish_approved_draft")
    def test_linkedin_publish_requires_confirmation(self, mock_publish):
        mock_publish.side_effect = ValueError("Publish cancelled: explicit confirmation is required.")

        response = self.client.post("/api/linkedin/draft/publish", json={"confirm_publish": False})
        self.assertEqual(response.status_code, 400)
        self.assertIn("explicit confirmation", response.json()["detail"])


    @patch("src.web.routers.settings.get_settings_payload")
    def test_settings_get_endpoint(self, mock_settings):
        mock_settings.return_value = {
            "target_roles": ["Senior Data Scientist"],
            "locations": ["Remote"],
            "include_keywords": ["machine learning"],
            "exclude_keywords": ["sales"],
            "daily_job_limit": 10,
            "posting_time_window": {"start_hour": 8, "end_hour": 11},
            "job_sources": {"remoteok": True},
            "secret_status": {
                "ANTHROPIC_API_KEY": {
                    "configured": False,
                    "description": "Required for Claude AI.",
                }
            },
            "editable_fields": ["target_roles"],
            "file_based_notes": ["Secrets are file-based."],
        }

        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["daily_job_limit"], 10)
        self.assertIn("secret_status", payload)

    @patch("src.web.routers.settings.update_settings_payload")
    def test_settings_update_endpoint(self, mock_update):
        mock_update.return_value = {
            "target_roles": ["Staff Data Scientist"],
            "locations": ["United States"],
            "include_keywords": ["healthcare"],
            "exclude_keywords": ["sales"],
            "daily_job_limit": 12,
            "posting_time_window": {"start_hour": 8, "end_hour": 10},
            "job_sources": {"remoteok": True, "himalayas": False},
            "secret_status": {
                "ANTHROPIC_API_KEY": {
                    "configured": True,
                    "description": "Required for Claude AI.",
                }
            },
            "editable_fields": ["target_roles"],
            "file_based_notes": ["Secrets are file-based."],
        }

        response = self.client.put(
            "/api/settings",
            json={
                "target_roles": ["Staff Data Scientist"],
                "locations": ["United States"],
                "include_keywords": ["healthcare"],
                "exclude_keywords": ["sales"],
                "daily_job_limit": 12,
                "posting_time_window": {"start_hour": 8, "end_hour": 10},
                "job_sources": {"remoteok": True, "himalayas": False},
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["daily_job_limit"], 12)

    def test_settings_update_rejects_invalid_window(self):
        response = self.client.put(
            "/api/settings",
            json={
                "target_roles": ["Staff Data Scientist"],
                "locations": ["United States"],
                "include_keywords": ["healthcare"],
                "exclude_keywords": [],
                "daily_job_limit": 12,
                "posting_time_window": {"start_hour": 10, "end_hour": 10},
                "job_sources": {"remoteok": True},
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("start must be earlier", response.json()["detail"])


    @patch("src.web.routers.runs.get_recent_runs")
    def test_runs_history_endpoint(self, mock_runs):
        mock_runs.return_value = [
            {
                "run_id": "abc123",
                "task_type": "jobs",
                "start_time": "2026-04-09T10:00:00+00:00",
                "end_time": "2026-04-09T10:00:15+00:00",
                "status": "success",
                "summary": "Scraped 3 jobs",
                "error_message": None,
            }
        ]

        response = self.client.get("/api/runs?limit=10")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["task_type"], "jobs")


    @patch("src.web.routers.scheduler.get_scheduler_status")
    def test_scheduler_status_endpoint(self, mock_scheduler_status):
        mock_scheduler_status.return_value = {
            "running": True,
            "timezone": "America/New_York",
            "started_at": "2026-04-09T12:00:00",
            "job_count": 2,
            "next_run_time": "2026-04-09T12:30:00+00:00",
            "jobs": [
                {
                    "job_id": "gmail_triage",
                    "name": "Gmail Triage",
                    "trigger": "interval[0:30:00]",
                    "next_run_time": "2026-04-09T12:30:00+00:00",
                }
            ],
        }

        response = self.client.get("/api/scheduler/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["running"])
        self.assertEqual(payload["job_count"], 2)

    @patch("src.web.routers.scheduler.start_scheduler")
    def test_scheduler_start_endpoint(self, mock_start):
        mock_start.return_value = {
            "running": True,
            "timezone": "America/New_York",
            "started_at": "2026-04-09T12:00:00",
            "job_count": 1,
            "next_run_time": None,
            "jobs": [],
        }

        response = self.client.post("/api/scheduler/start", json={"confirm_action": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["running"])

    @patch("src.web.routers.scheduler.stop_scheduler")
    def test_scheduler_stop_endpoint(self, mock_stop):
        mock_stop.return_value = {
            "running": False,
            "timezone": "America/New_York",
            "started_at": None,
            "job_count": 0,
            "next_run_time": None,
            "jobs": [],
        }

        response = self.client.post("/api/scheduler/stop", json={"confirm_action": True})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["running"])


    def test_scheduler_start_requires_confirmation(self):
        response = self.client.post("/api/scheduler/start", json={"confirm_action": False})
        self.assertEqual(response.status_code, 400)
        self.assertIn("explicit confirmation", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
