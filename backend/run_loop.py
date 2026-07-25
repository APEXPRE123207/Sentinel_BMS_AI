"""
SentinelAI - Closed Loop Control Runner
Orchestrates the complete closed-loop autonomous control cycle:
Observe -> State Manager -> Rolling Context Builder -> Agent Council -> Safety Validator -> Forward Controller -> Execute -> DB Log.

Set use_energyplus=True to connect to the real EnergyPlus simulation (D:\\EnergyPlus must be installed).
Set use_energyplus=False (default) to use the built-in multi-zone physics engine for fast testing.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from .database.db import DatabaseManager
from .state.state_manager import StateManager
from .state.context_builder import RollingContextBuilder
from .agents.council import AgentCouncil
from .validator.safety_validator import SafetyValidator
from .controller.forward_controller import ForwardController
from .health_engine.engine import EquipmentHealthEngine
from .energyplus.runner import EnergyPlusRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SentinelAI")

class SentinelAIControlLoop:
    def __init__(
        self,
        db_path: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        max_retries: int = 1,
        use_energyplus: bool = False,
        idf_path: Optional[str] = None,
        epw_path: Optional[str] = None,
    ):
        self.db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        self.state_manager = StateManager(self.db_manager)
        self.context_builder = RollingContextBuilder(window_size=10)
        self.agent_council = AgentCouncil(api_url=llm_api_url)
        self.validator = SafetyValidator()
        self.health_engine = EquipmentHealthEngine()
        self.max_retries = max_retries
        self.use_energyplus = use_energyplus

        if use_energyplus:
            kwargs = {}
            if idf_path:
                kwargs["idf_path"] = idf_path
            if epw_path:
                kwargs["epw_path"] = epw_path
            self.simulator = EnergyPlusRunner(**kwargs)
            self.simulator.start()
            logger.info("SentinelAI running with REAL EnergyPlus simulation.")
        else:
            raise NotImplementedError("The mock physics engine has been removed. You must use use_energyplus=True.")

        self.controller = ForwardController(self.simulator)

    def run_step(self) -> Dict[str, Any]:
        """
        Executes a single 1-step autonomous closed-loop cycle.
        """
        # Step 1: Advance simulation & observe live telemetry
        sim_data = self.simulator.step()
        
        # Step 2: State Manager (Single source of truth & SQLite logging)
        building_state = self.state_manager.update_state(
            timestep=sim_data["timestep"],
            outdoor_temp=sim_data["outdoor_temp"],
            outdoor_humidity=sim_data["outdoor_humidity"],
            zones_data=sim_data["zones"],
            equipment_data=sim_data["equipment"],
            total_energy_kwh=sim_data["total_energy_kwh"],
            carbon_emissions_kg=sim_data["carbon_emissions_kg"]
        )

        # Step 2.5: Evaluate Equipment Health Engine
        health_report = self.health_engine.evaluate_state(building_state)
        self.db_manager.log_equipment_health_report(health_report)

        # Step 3: Rolling Context Builder
        self.context_builder.add_state(building_state)
        context_prompt_data = self.context_builder.build_context(building_state)

        # Step 4: Agent Council Reasoning
        council_decision = self.agent_council.evaluate(context_prompt_data)
        self.db_manager.log_agent_decision(council_decision)

        # Step 5: Safety Validator with Self-Correcting Retry Loop & LKG Fallback
        current_setpoints = {z_id: z.target_setpoint for z_id, z in building_state.zones.items()}
        attempt = 1
        rejection_reason = None

        val_result = self.validator.validate(
            action=council_decision.recommended_action,
            building_state=building_state,
            attempt_number=attempt,
            current_setpoints=current_setpoints
        )

        while not val_result.is_valid and attempt <= self.max_retries:
            logger.warning(f"Timestep {building_state.timestep} - Safety Rejection (Attempt {attempt}): {val_result.rejection_reason}")
            self.db_manager.log_validation_result(building_state.timestep, time.time(), val_result)
            
            attempt += 1
            rejection_reason = self.validator.build_feedback_prompt(val_result)

            # Retry Agent Council with feedback prompt
            retry_decision = self.agent_council.evaluate(
                context_prompt_data,
                rejection_feedback=rejection_reason
            )
            self.db_manager.log_agent_decision(retry_decision)

            val_result = self.validator.validate(
                action=retry_decision.recommended_action,
                building_state=building_state,
                attempt_number=attempt,
                current_setpoints=current_setpoints
            )

        # Log final validation result
        self.db_manager.log_validation_result(building_state.timestep, time.time(), val_result)

        action_to_apply = val_result.applied_action or val_result.action

        # Step 6: Forward Controller Actuation
        actuation_result = self.controller.apply_action(action_to_apply)

        logger.info(
            f"Timestep {building_state.timestep} Completed | Outdoor: {building_state.outdoor_temp}°C | "
            f"Energy: {building_state.total_energy_kwh} kWh | Health: {health_report.overall_health_score}% | "
            f"Validated: {val_result.is_valid} | Fallback: {val_result.used_fallback}"
        )

        return {
            "timestep": building_state.timestep,
            "building_state": building_state,
            "health_report": health_report,
            "council_decision": council_decision,
            "validation_result": val_result,
            "actuation_result": actuation_result
        }

    def run_n_steps(self, num_steps: int = 10) -> List[Dict[str, Any]]:
        results = []
        try:
            for i in range(num_steps):
                results.append(self.run_step())
        finally:
            if self.use_energyplus and hasattr(self.simulator, 'stop'):
                self.simulator.stop()
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SentinelAI Autonomous Building Control Loop")
    parser.add_argument("--steps", type=int, default=10, help="Number of control steps to run")
    parser.add_argument("--energyplus", action="store_true", help="Use real EnergyPlus simulation")
    parser.add_argument("--idf", type=str, default=None, help="Path to .idf building model")
    parser.add_argument("--epw", type=str, default=None, help="Path to .epw weather file")
    args = parser.parse_args()

    loop = SentinelAIControlLoop(
        use_energyplus=args.energyplus,
        idf_path=args.idf,
        epw_path=args.epw,
    )
    loop.run_n_steps(args.steps)
