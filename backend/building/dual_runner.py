"""
SentinelAI - Dual Simulation Runner (Phase 3)
Orchestrates running the un-controlled Baseline EnergyPlus simulation
and the SentinelAI-controlled simulation cleanly without C-API DLL thread conflicts.
Runs Baseline metrics collection first, persists to SQLite BaselineMetrics,
then runs SentinelAI and compares live results step-by-step against SQLite BaselineMetrics.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from ..database.db import DatabaseManager
from ..analytics.comparator import BaselineComparator
from ..run_loop import SentinelAIControlLoop
from .baseline_runner import BaselineSimulationRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DualSimulation")

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASELINE_IDF = os.path.join(_HERE, "baseline.idf")
_SENTINEL_IDF = os.path.join(_HERE, "sentinel.idf")
_WEATHER_EPW = os.path.join(_HERE, "weather.epw")

class DualSimulationRunner:
    def __init__(
        self,
        db_path: Optional[str] = None,
        use_energyplus: bool = True,
        llm_api_url: Optional[str] = None
    ):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        self.comparator = BaselineComparator(self.db_manager)
        self.use_energyplus = use_energyplus
        self.llm_api_url = llm_api_url

    def run_dual_simulation(self, num_steps: int = 10) -> List[Dict[str, Any]]:
        """
        Executes Phase 1: Baseline EnergyPlus simulation (persisting to BaselineMetrics SQLite table).
        Executes Phase 2: SentinelAI EnergyPlus simulation (evaluating against BaselineMetrics).
        Returns list of comparative step reports.
        """
        logger.info("=== STEP 1: Running Baseline EnergyPlus Simulation ===")
        baseline_runner = BaselineSimulationRunner(
            db_manager=self.db_manager,
            idf_path=_BASELINE_IDF,
            epw_path=_WEATHER_EPW,
            use_energyplus=self.use_energyplus
        )

        try:
            for i in range(num_steps):
                b_metrics = baseline_runner.run_step()
                logger.info(f"Baseline Timestep {b_metrics['timestep']} | Energy: {b_metrics['total_energy_kwh']} kWh | PMV: {b_metrics['avg_pmv']}")
        finally:
            baseline_runner.stop()

        logger.info("=== STEP 2: Running SentinelAI Control Loop Simulation ===")
        ai_loop = SentinelAIControlLoop(
            db_path=self.db_path,
            llm_api_url=self.llm_api_url,
            use_energyplus=self.use_energyplus,
            idf_path=_SENTINEL_IDF,
            epw_path=_WEATHER_EPW
        )

        results = []
        try:
            for i in range(num_steps):
                ai_res = ai_loop.run_step()
                ai_state = ai_res["building_state"]

                # Fetch corresponding baseline timestep metrics from SQLite
                comp_res = self.comparator.evaluate_timestep(ai_state)
                results.append(comp_res)

                logger.info(
                    f"Dual Timestep {ai_state.timestep} | "
                    f"Baseline Energy: {comp_res['baseline']['energy_kwh']} kWh | "
                    f"AI Energy: {comp_res['sentinel_ai']['energy_kwh']} kWh | "
                    f"Energy Saved: {comp_res['comparison']['energy_saved_pct']}% | "
                    f"Carbon Reduced: {comp_res['comparison']['carbon_reduced_pct']}% | "
                    f"Comfort Improvement: {comp_res['comparison']['comfort_improvement']}"
                )
        finally:
            if hasattr(ai_loop.simulator, "stop"):
                ai_loop.simulator.stop()

        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SentinelAI Dual Simulation Runner (Baseline vs AI)")
    parser.add_argument("--steps", type=int, default=10, help="Number of dual simulation steps")
    parser.add_argument("--no-energyplus", action="store_true", help="Use built-in physics engine instead of EnergyPlus")
    args = parser.parse_args()

    runner = DualSimulationRunner(use_energyplus=not args.no_energyplus)
    runner.run_dual_simulation(args.steps)
