"""
SentinelAI - Closed Loop Control Runner
Orchestrates the complete closed-loop autonomous control cycle:
Observe -> State Manager -> Rolling Context Builder -> Agent Council -> Safety Validator -> Forward Controller -> Execute -> DB Log.

EnergyPlus is the only supported simulation backend.
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
# Pygame Digital Twin removed — visualization is now handled by the in-browser Canvas
try:
    from .building.idf_modifier import configure_idf
except ModuleNotFoundError:
    def configure_idf():
        return None
import json
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SentinelAI")

class SentinelAIControlLoop:
    def __init__(
        self,
        db_path: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        max_retries: int = 1,
        use_energyplus: bool = True,
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
        self.use_energyplus = True
        self.control_step = 0

        kwargs = {}

        # Step 0: Apply pre-run configuration (city, occupants, start date)
        configure_idf()

        config_path = os.path.join(os.path.dirname(__file__), "..", "run_config.json")
        base_idf_name = "small_office.idf"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
                base_idf_name = cfg.get("base_idf_name", "small_office.idf")
                if "epw_path" in cfg and cfg["epw_path"]:
                    abs_epw = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", cfg["epw_path"]))
                    kwargs["epw_path"] = abs_epw

        configured_idf_name = base_idf_name.replace(".idf", "_configured.idf")
        configured_idf = os.path.join(os.path.dirname(__file__), "building", configured_idf_name)
        kwargs["idf_path"] = configured_idf if os.path.exists(configured_idf) else os.path.join(os.path.dirname(__file__), "building", base_idf_name)

        if idf_path:
            kwargs["idf_path"] = idf_path
        if epw_path:
            kwargs["epw_path"] = epw_path

        self.simulator = EnergyPlusRunner(**kwargs)
        self.simulator.start()
        self.using_energyplus_backend = True
        logger.info("SentinelAI running with REAL EnergyPlus simulation.")

        self.controller = ForwardController(self.simulator)
        
        # Digital Twin visualization is now rendered in the browser (Canvas in index.html)
        self.pending_validation_result = None
        self.pending_building_state = None
        self.pending_health_report = None
        self.pending_council_decision = None
        self.pending_loop_timestep = 0

    def propose_step(self) -> Dict[str, Any]:
        """
        Executes the autonomous loop up to the safety validation step, but DOES NOT apply to controller.
        """
        self.control_step += 1
        loop_timestep = self.control_step

        # Step 1: Advance simulation & observe live telemetry
        sim_data = self.simulator.step()
        
        # Step 2: State Manager (Single source of truth & SQLite logging)
        building_state = self.state_manager.update_state(
            timestep=loop_timestep,
            outdoor_temp=sim_data["outdoor_temp"],
            outdoor_humidity=sim_data["outdoor_humidity"],
            zones_data=sim_data["zones"],
            equipment_data=sim_data["equipment"],
            grid_carbon_intensity=sim_data.get("grid_carbon_intensity", 0.45),
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

        self.pending_validation_result = val_result
        self.pending_building_state = building_state
        self.pending_health_report = health_report
        self.pending_council_decision = council_decision
        self.pending_loop_timestep = loop_timestep

        return {
            "timestep": loop_timestep,
            "building_state": building_state,
            "health_report": health_report,
            "council_decision": council_decision,
            "validation_result": val_result,
            "status": "PROPOSED"
        }

    def apply_step(self, mcp_action_to_apply=None) -> Dict[str, Any]:
        """
        Applies the pending validated action (or a manually confirmed MCP action) to the controller.
        """
        if not self.pending_validation_result:
            raise ValueError("No pending step to apply. Call propose_step() first.")

        # If MCP provided an explicitly confirmed action, use it, otherwise use the AI's validated action
        action_to_apply = mcp_action_to_apply or self.pending_validation_result.applied_action or self.pending_validation_result.action

        # Step 6: Forward Controller Actuation
        actuation_result = self.controller.apply_action(action_to_apply)

        logger.info(
            f"Timestep {self.pending_building_state.timestep} Completed | Outdoor: {self.pending_building_state.outdoor_temp}°C | "
            f"Energy: {self.pending_building_state.total_energy_kwh} kWh | Health: {self.pending_health_report.overall_health_score}% | "
            f"Validated: {self.pending_validation_result.is_valid} | Fallback: {self.pending_validation_result.used_fallback}"
        )

        res = {
            "timestep": self.pending_loop_timestep,
            "building_state": self.pending_building_state,
            "health_report": self.pending_health_report,
            "council_decision": self.pending_council_decision,
            "validation_result": self.pending_validation_result,
            "actuation_result": actuation_result
        }
        
        # Clear pending
        self.pending_validation_result = None
        self.pending_building_state = None
        
        return res

    def run_step(self) -> Dict[str, Any]:
        """Backward compatible full-cycle run_step."""
        self.propose_step()
        return self.apply_step()

    def run_n_steps(self, num_steps: int = 10) -> List[Dict[str, Any]]:
        results = []
        try:
            for i in range(num_steps):
                results.append(self.run_step())
        finally:
            if hasattr(self.simulator, 'stop'):
                self.simulator.stop()
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SentinelAI Autonomous Building Control Loop")
    parser.add_argument("--steps", type=int, default=10, help="Number of control steps to run")
    parser.add_argument("--idf", type=str, default=None, help="Path to .idf building model")
    parser.add_argument("--epw", type=str, default=None, help="Path to .epw weather file")
    args = parser.parse_args()

    loop = SentinelAIControlLoop(
        idf_path=args.idf,
        epw_path=args.epw,
    )
    loop.run_n_steps(args.steps)
