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


if __name__ == "__main__":
    unittest.main()
