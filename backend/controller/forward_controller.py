"""
SentinelAI - Forward Controller
Translates validated AI decisions into specific actuator control commands
and updates the target simulation parameters.
"""
from typing import Dict, Any
from ..database.models import ActionRecommendation

class ForwardController:
    def __init__(self, simulator=None):
        self.simulator = simulator

    def set_simulator(self, simulator):
        self.simulator = simulator

    def apply_action(self, action: ActionRecommendation) -> Dict[str, Any]:
        """
        Executes the validated action on the active simulation environment.
        """
        results = {
            "applied_setpoints": action.zone_setpoints,
            "applied_airflows": action.zone_airflows,
            "applied_lighting": action.zone_lighting,
            "applied_ventilation": action.ventilation_rate,
            "pump_switched": action.pump_switch_active
        }

        if self.simulator and hasattr(self.simulator, "apply_actuators"):
            self.simulator.apply_actuators(
                setpoints=action.zone_setpoints,
                airflows=action.zone_airflows,
                lighting=action.zone_lighting,
                ventilation=action.ventilation_rate,
                pump_switch=action.pump_switch_active
            )

        return results
