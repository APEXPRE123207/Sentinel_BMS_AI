"""
SentinelAI - Closed Loop System Tests
Verifies database persistence, state management, rolling context building,
agent council decisions, safety validation, retry fallback, and full 10-step closed loop execution.
"""
import os
import tempfile
import unittest
from backend.database.db import DatabaseManager
from backend.database.models import BuildingState, ZoneState, EquipmentTelemetry, ActionRecommendation
from backend.state.state_manager import StateManager
from backend.state.context_builder import RollingContextBuilder
from backend.agents.council import AgentCouncil
from backend.validator.safety_validator import SafetyValidator
from backend.run_loop import SentinelAIControlLoop

class TestClosedLoop(unittest.TestCase):

    def test_database_initialization_and_logging(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            db = DatabaseManager(db_path)
            state_mgr = StateManager(db)

            zones_data = {
                "Office": {"temperature": 23.5, "target_setpoint": 22.0, "humidity": 50.0, "co2": 420.0, "pmv": 0.2, "occupancy": 5, "airflow": 0.5, "lighting_level": 0.8}
            }
            equip_data = {
                "ahu_status": "NORMAL", "ahu_health": 95.0,
                "pump_status": "NORMAL", "pump_health": 85.0,
                "fan_status": "NORMAL", "fan_health": 90.0,
                "chiller_status": "NORMAL", "chiller_health": 99.0,
                "total_power_kw": 12.0, "cumulative_runtime_hours": 50.0, "cycling_count": 2
            }

            state = state_mgr.update_state(
                timestep=1, outdoor_temp=26.0, outdoor_humidity=45.0,
                zones_data=zones_data, equipment_data=equip_data,
                total_energy_kwh=3.0, carbon_emissions_kg=1.35
            )

            self.assertEqual(state.timestep, 1)
            self.assertIn("Office", state.zones)
            self.assertEqual(state.zones["Office"].temperature, 23.5)

            # Check DB connection & row count
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BuildingState;")
                count = cursor.fetchone()[0]
                self.assertEqual(count, 1)

                cursor.execute("SELECT COUNT(*) FROM EquipmentHealth;")
                health_count = cursor.fetchone()[0]
                self.assertEqual(health_count, 1)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    def test_rolling_context_builder(self):
        context_builder = RollingContextBuilder(window_size=5)
        for i in range(1, 10):
            state = BuildingState(
                timestep=i,
                outdoor_temp=20.0 + i,
                total_energy_kwh=i * 2.0,
                carbon_emissions_kg=i * 0.9,
                zones={"Office": ZoneState(zone_id="Office", temperature=21.0 + i * 0.2, target_setpoint=22.0, humidity=50.0, co2=400.0, pmv=0.1*i, occupancy=2, airflow=0.5, lighting_level=0.8)}
            )
            context_builder.add_state(state)

        ctx = context_builder.build_context(state)
        self.assertEqual(ctx["timestep"], 9)
        self.assertEqual(ctx["rolling_trend_summary"]["window_size"], 5)
        self.assertGreater(ctx["rolling_trend_summary"]["zone_min_temp_c"], 0)

    def test_safety_validator_and_fallback(self):
        validator = SafetyValidator(min_setpoint_c=19.0, max_setpoint_c=26.0)

        # Valid Action
        valid_action = ActionRecommendation(
            zone_setpoints={"Office": 22.0}
        )
        res_valid = validator.validate(valid_action, attempt_number=1)
        self.assertTrue(res_valid.is_valid)

        # Invalid Action (temperature out of range)
        invalid_action = ActionRecommendation(
            zone_setpoints={"Office": 15.0} # Below 19°C limit
        )
        res_invalid = validator.validate(invalid_action, attempt_number=1)
        self.assertFalse(res_invalid.is_valid)
        self.assertGreater(len(res_invalid.violated_rules), 0)

        # Retry 2 should fallback to Last Known Good action
        res_retry = validator.validate(invalid_action, attempt_number=2)
        self.assertFalse(res_retry.is_valid)
        self.assertTrue(res_retry.used_fallback)
        self.assertEqual(res_retry.applied_action.zone_setpoints["Office"], 22.0)

    def test_full_closed_loop_execution(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            loop = SentinelAIControlLoop(db_path=db_path)
            results = loop.run_n_steps(10)

            self.assertEqual(len(results), 10)
            self.assertEqual(results[0]["timestep"], 1)
            self.assertEqual(results[9]["timestep"], 10)

            # Confirm DB recorded all decisions & state
            with loop.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BuildingState;")
                self.assertEqual(cursor.fetchone()[0], 10)

                cursor.execute("SELECT COUNT(*) FROM AgentDecision;")
                self.assertGreaterEqual(cursor.fetchone()[0], 10)

                cursor.execute("SELECT COUNT(*) FROM ValidatorLog;")
                self.assertGreaterEqual(cursor.fetchone()[0], 10)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

if __name__ == "__main__":
    unittest.main()
