"""
SentinelAI - Phase 3 Baseline Comparison Test Suite
Verifies BaselineMetrics, AISimulationMetrics logging, BaselineComparator metrics math,
and side-by-side Dual Simulation execution.
"""
import os
import tempfile
import unittest
from backend.database.db import DatabaseManager
from backend.database.models import BuildingState, ZoneState, EquipmentTelemetry
from backend.analytics.comparator import BaselineComparator
from backend.building.baseline_runner import BaselineSimulationRunner
from backend.building.dual_runner import DualSimulationRunner

class TestBaselineComparison(unittest.TestCase):

    def test_database_baseline_tables(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            db = DatabaseManager(db_path)
            db.log_baseline_metrics(
                timestep=1, timestamp=100.0, total_energy_kwh=10.0,
                avg_pmv=0.5, carbon_emissions_kg=4.5, equipment_stress_score=15.0
            )
            db.log_ai_simulation_metrics(
                timestep=1, timestamp=100.0, total_energy_kwh=8.0,
                avg_pmv=0.1, carbon_emissions_kg=3.6, equipment_stress_score=12.0,
                energy_saved_pct=20.0, carbon_reduced_pct=20.0
            )

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BaselineMetrics;")
                self.assertEqual(cursor.fetchone()[0], 1)

                cursor.execute("SELECT COUNT(*) FROM AISimulationMetrics;")
                self.assertEqual(cursor.fetchone()[0], 1)

                row = db.get_latest_baseline_metrics(1)
                self.assertIsNotNone(row)
                self.assertEqual(row["total_energy_kwh"], 10.0)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    def test_comparator_math(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            db = DatabaseManager(db_path)
            comparator = BaselineComparator(db)

            # Baseline: 10.0 kWh, 4.5 kg carbon, PMV 0.8
            baseline_data = {
                "total_energy_kwh": 10.0,
                "carbon_emissions_kg": 4.5,
                "avg_pmv": 0.8,
                "equipment_stress_score": 20.0
            }

            # AI State: 8.0 kWh (20% saved), 3.6 kg carbon (20% reduced), PMV 0.2
            ai_state = BuildingState(
                timestep=1,
                total_energy_kwh=8.0,
                carbon_emissions_kg=3.6,
                zones={
                    "Office": ZoneState(zone_id="Office", temperature=22.0, target_setpoint=22.0, humidity=50.0, co2=400.0, pmv=0.2, occupancy=5, airflow=0.5, lighting_level=0.8)
                },
                telemetry=EquipmentTelemetry(
                    ahu_status="NORMAL", ahu_health=95.0, pump_status="NORMAL", pump_health=85.0,
                    fan_status="NORMAL", fan_health=90.0, chiller_status="NORMAL", chiller_health=95.0,
                    total_power_kw=15.0, cumulative_runtime_hours=10.0, cycling_count=2
                )
            )

            res = comparator.evaluate_timestep(ai_state, baseline_data=baseline_data)

            self.assertEqual(res["comparison"]["energy_saved_pct"], 20.0)
            self.assertEqual(res["comparison"]["carbon_reduced_pct"], 20.0)
            self.assertEqual(res["comparison"]["comfort_improvement"], 0.6)  # |0.8| - |0.2| = 0.6
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    def test_baseline_simulation_runner(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            db = DatabaseManager(db_path)
            runner = BaselineSimulationRunner(db_manager=db, use_energyplus=False)
            metrics = runner.run_step()

            self.assertEqual(metrics["timestep"], 1)
            self.assertGreaterEqual(metrics["total_energy_kwh"], 0.0)

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BaselineMetrics;")
                self.assertEqual(cursor.fetchone()[0], 1)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    def test_dual_simulation_runner(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()

        try:
            runner = DualSimulationRunner(db_path=db_path, use_energyplus=False)
            results = runner.run_dual_simulation(num_steps=5)

            self.assertEqual(len(results), 5)
            self.assertEqual(results[0]["timestep"], 1)
            self.assertEqual(results[4]["timestep"], 5)

            with runner.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BaselineMetrics;")
                self.assertEqual(cursor.fetchone()[0], 5)

                cursor.execute("SELECT COUNT(*) FROM AISimulationMetrics;")
                self.assertEqual(cursor.fetchone()[0], 5)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

if __name__ == "__main__":
    unittest.main()
