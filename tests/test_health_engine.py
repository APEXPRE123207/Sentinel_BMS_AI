"""
SentinelAI - Phase 4 Equipment Health Engine Test Suite
Tests health score degradation, stress index calculation, RUL forecasting,
anomaly detection, predictive maintenance alerts, and SQLite persistence.
"""
import os
import tempfile
import unittest
from backend.database.db import DatabaseManager
from backend.database.models import BuildingState, ZoneState, EquipmentTelemetry
from backend.health_engine.models import (
    EquipmentType, AlertSeverity, OverallBuildingHealthReport
)
from backend.health_engine.engine import EquipmentHealthEngine
from backend.run_loop import SentinelAIControlLoop

class TestEquipmentHealthEngine(unittest.TestCase):

    def setUp(self):
        self.engine = EquipmentHealthEngine()

    def _make_state(self, timestep=1, power_kw=15.0, runtime_hours=100.0, cycling_count=2):
        return BuildingState(
            timestep=timestep,
            outdoor_temp=25.0,
            outdoor_humidity=50.0,
            zones={
                "Office": ZoneState(zone_id="Office", temperature=23.0, target_setpoint=22.0, humidity=50.0, co2=420.0, pmv=0.2, occupancy=5, airflow=0.5, lighting_level=0.8)
            },
            telemetry=EquipmentTelemetry(
                ahu_status="NORMAL", ahu_health=98.0,
                pump_status="NORMAL", pump_health=78.0,
                fan_status="NORMAL", fan_health=95.0,
                chiller_status="NORMAL", chiller_health=92.0,
                total_power_kw=power_kw,
                cumulative_runtime_hours=runtime_hours,
                cycling_count=cycling_count
            ),
            total_energy_kwh=10.0,
            carbon_emissions_kg=4.5
        )

    def test_initial_health_evaluation(self):
        state = self._make_state(timestep=1, power_kw=12.0)
        report = self.engine.evaluate_state(state)

        self.assertIsInstance(report, OverallBuildingHealthReport)
        self.assertGreater(report.overall_health_score, 80.0)
        self.assertIn("AHU", report.assets)
        self.assertIn("CHILLER", report.assets)
        self.assertIn("PUMP", report.assets)
        self.assertIn("FAN", report.assets)

    def test_stress_index_and_rul(self):
        state = self._make_state(timestep=5, power_kw=15.0, runtime_hours=1000.0, cycling_count=10)
        report = self.engine.evaluate_state(state)

        chiller_report = report.assets["CHILLER"]
        self.assertGreater(chiller_report.stress_index, 0.0)
        self.assertGreater(chiller_report.rul_hours, 0.0)
        self.assertLess(chiller_report.rul_hours, 60000.0)

    def test_overload_and_rapid_cycling_degradation(self):
        initial_chiller_health = self.engine.health_scores[EquipmentType.CHILLER]

        # Simulate electrical overload surge (> 25 kW) and cycling jump
        state_overload = self._make_state(timestep=10, power_kw=32.0, cycling_count=6)
        report = self.engine.evaluate_state(state_overload)

        new_chiller_health = self.engine.health_scores[EquipmentType.CHILLER]
        self.assertLess(new_chiller_health, initial_chiller_health)
        self.assertGreater(len(report.building_anomalies), 0)

    def test_anomaly_detection_power_surge(self):
        state = self._make_state(power_kw=35.0)
        report = self.engine.evaluate_state(state)

        anom_types = [a.anomaly_type for a in report.building_anomalies]
        self.assertIn("POWER_SPIKE_SURGE", anom_types)

    def test_predictive_alerts_generation(self):
        # Force low health score on Pump
        self.engine.health_scores[EquipmentType.PUMP] = 45.0
        state = self._make_state()
        report = self.engine.evaluate_state(state)

        severities = [a.severity for a in report.active_alerts]
        self.assertIn(AlertSeverity.CRITICAL, severities)

    def test_regeneration_switch(self):
        self.engine.health_scores[EquipmentType.PUMP] = 50.0
        self.engine.apply_regeneration_switch(EquipmentType.PUMP, boost_pct=20.0)

        self.assertEqual(self.engine.health_scores[EquipmentType.PUMP], 70.0)
        self.assertEqual(self.engine.statuses[EquipmentType.PUMP], "REGENERATED")

    def test_closed_loop_health_integration(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            loop = SentinelAIControlLoop(db_path=db_path, use_energyplus=False)
            res = loop.run_step()

            self.assertIn("health_report", res)
            self.assertGreater(res["health_report"].overall_health_score, 0.0)

            latest = loop.db_manager.get_latest_equipment_health()
            self.assertIsNotNone(latest)
            self.assertIn("ahu_health", latest)
            self.assertIn("chiller_health", latest)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

if __name__ == "__main__":
    unittest.main()
