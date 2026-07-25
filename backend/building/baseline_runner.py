"""
SentinelAI - Baseline EnergyPlus Simulation Runner (Phase 3)
Runs the un-controlled baseline building model (baseline.idf) using pyenergyplus.api
with standard static thermostat schedules and no AI intervention.
Logs step metrics directly to SQLite BaselineMetrics table.
"""
import sys
import os
import time
import logging
from typing import Dict, Any, Optional
from ..database.db import DatabaseManager
from ..energyplus.runner import EnergyPlusRunner, SimulationEngine

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASELINE_IDF = os.path.join(_HERE, "baseline.idf")
_WEATHER_EPW = os.path.join(_HERE, "weather.epw")

class BaselineSimulationRunner:
    def __init__(
        self,
        db_manager: DatabaseManager,
        idf_path: str = _BASELINE_IDF,
        epw_path: str = _WEATHER_EPW,
        use_energyplus: bool = True
    ):
        self.db_manager = db_manager
        self.use_energyplus = use_energyplus

        if use_energyplus and os.path.exists(idf_path) and os.path.exists(epw_path):
            self.runner = EnergyPlusRunner(idf_path=idf_path, epw_path=epw_path)
            self.runner.start()
        else:
            self.runner = SimulationEngine()

    def run_step(self) -> Dict[str, Any]:
        """
        Advances baseline simulation by 1 timestep and records baseline metrics to SQLite.
        """
        step_data = self.runner.step()
        timestep = step_data["timestep"]

        total_energy_kwh = step_data.get("total_energy_kwh", 0.0)
        carbon_emissions_kg = step_data.get("carbon_emissions_kg", 0.0)

        zones = step_data.get("zones", {})
        zone_pmvs = [z.get("pmv", 0.0) for z in zones.values()]
        avg_pmv = sum(zone_pmvs) / len(zone_pmvs) if zone_pmvs else 0.0

        equipment = step_data.get("equipment", {})
        power_kw = equipment.get("total_power_kw", 0.0)
        cycling = equipment.get("cycling_count", 0)
        stress_score = power_kw * (1.0 + (cycling * 0.05))

        timestamp = time.time()

        # Log directly to BaselineMetrics SQLite table
        self.db_manager.log_baseline_metrics(
            timestep=timestep,
            timestamp=timestamp,
            total_energy_kwh=total_energy_kwh,
            avg_pmv=round(avg_pmv, 2),
            carbon_emissions_kg=carbon_emissions_kg,
            equipment_stress_score=round(stress_score, 2)
        )

        return {
            "timestep": timestep,
            "total_energy_kwh": total_energy_kwh,
            "avg_pmv": round(avg_pmv, 2),
            "carbon_emissions_kg": carbon_emissions_kg,
            "equipment_stress_score": round(stress_score, 2)
        }

    def stop(self):
        if hasattr(self.runner, "stop"):
            self.runner.stop()
