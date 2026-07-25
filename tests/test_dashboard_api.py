"""
SentinelAI - Phase 5 Dashboard REST API Test Suite
Verifies FastAPI endpoints for system status, building state history,
Agent Council decisions, Safety Validator logs, Equipment Health diagnostics,
baseline comparison, and control step triggers.
"""
import os
import tempfile
import unittest

try:
    from fastapi.testclient import TestClient
    from backend.api.main import app, db_manager
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

class TestDashboardAPI(unittest.TestCase):

    def setUp(self):
        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed in current Python environment")
        self.client = TestClient(app)

    def test_system_status_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("total_recorded_steps", data)

    def test_state_latest_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/state/latest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_state_history_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/state/history?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_council_latest_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/council/latest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_validator_logs_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/validator/logs?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_health_latest_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/health/latest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("overall_health_score", data)

    def test_comparison_latest_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/api/comparison/latest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("comfort_improvement", data)

    def test_control_step_endpoint(self):
        if not HAS_FASTAPI:
            return
        response = self.client.post("/api/control/step")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("timestep", data)

    def test_dashboard_html_serve(self):
        if not HAS_FASTAPI:
            return
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("SentinelAI", response.text)

if __name__ == "__main__":
    unittest.main()
