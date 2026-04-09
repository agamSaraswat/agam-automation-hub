import unittest

from src.jobs.filtering import apply_relevance_filter, evaluate_job_relevance, get_relevance_config


class JobFilteringTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "locations": ["Remote", "United States"],
            "target_roles": ["Senior Data Scientist"],
            "filters": {
                "include_keywords": ["machine learning", "healthcare", "nlp"],
                "exclude_keywords": ["sales", "frontend"],
                "include_titles": ["senior data scientist", "nlp engineer"],
                "exclude_titles": ["intern", "director"],
                "preferred_locations": ["remote", "united states"],
                "remote_preference": True,
                "minimum_match_threshold": 25,
            },
        }

    def test_keeps_high_fit_job(self):
        relevance = get_relevance_config(self.config)
        job = {
            "title": "Senior Data Scientist, Healthcare AI",
            "jd_text": "Machine learning models for healthcare NLP pipelines.",
            "location": "Remote - United States",
            "source": "remoteok",
        }

        decision = evaluate_job_relevance(job, relevance)
        self.assertTrue(decision["keep"])
        self.assertGreaterEqual(decision["match_score"], relevance["minimum_match_threshold"])
        self.assertTrue(decision["reasons"])

    def test_rejects_excluded_title(self):
        relevance = get_relevance_config(self.config)
        job = {
            "title": "Data Science Intern",
            "jd_text": "Help with dashboards and analysis.",
            "location": "Remote",
        }

        decision = evaluate_job_relevance(job, relevance)
        self.assertFalse(decision["keep"])
        self.assertIn("Blocked title", decision["reject_reason"])

    def test_rejects_excluded_keyword(self):
        relevance = get_relevance_config(self.config)
        job = {
            "title": "Senior Data Scientist",
            "jd_text": "Sales analytics and frontend optimization role.",
            "location": "United States",
        }

        decision = evaluate_job_relevance(job, relevance)
        self.assertFalse(decision["keep"])
        self.assertIn("Blocked keyword", decision["reject_reason"])

    def test_apply_relevance_filter_splits_kept_and_rejected(self):
        jobs = [
            {
                "title": "Senior Data Scientist",
                "company": "A",
                "location": "Remote",
                "jd_text": "Machine learning and healthcare NLP",
                "source": "remoteok",
            },
            {
                "title": "Director of Sales",
                "company": "B",
                "location": "Boston",
                "jd_text": "Sales leadership",
                "source": "indeed",
            },
        ]

        kept, rejected = apply_relevance_filter(jobs, self.config)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(kept[0]["company"], "A")
        self.assertEqual(rejected[0]["company"], "B")


if __name__ == "__main__":
    unittest.main()
