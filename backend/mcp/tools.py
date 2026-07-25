"""
SentinelAI - MCP Tool Server Definitions
Provides Model Context Protocol (MCP) compatible tools for interacting with building state,
retrieving sensor metrics, and issuing actuation controls.
"""
from typing import Dict, Any, Optional
from ..database.models import BuildingState, ActionRecommendation

class MCPToolServer:
    def __init__(self):
        self.latest_state: Optional[BuildingState] = None
        self.pending_action: ActionRecommendation = ActionRecommendation()

    def update_state(self, state: BuildingState):
        self.latest_state = state

    # --- Sensor Tools ---
    def get_zone_temperature(self, zone_id: str) -> Dict[str, Any]:
        if not self.latest_state or zone_id not in self.latest_state.zones:
            return {"error": f"Zone {zone_id} not found", "temperature": None}
        z = self.latest_state.zones[zone_id]
        return {
            "zone_id": zone_id,
            "temperature": z.temperature,
            "setpoint": z.target_setpoint,
            "humidity": z.humidity,
            "pmv": z.pmv,
            "co2": z.co2
        }

    def get_energy_usage(self) -> Dict[str, Any]:
        if not self.latest_state:
            return {"total_energy_kwh": 0.0, "carbon_emissions_kg": 0.0}
        return {
            "total_energy_kwh": self.latest_state.total_energy_kwh,
            "carbon_emissions_kg": self.latest_state.carbon_emissions_kg,
            "grid_carbon_intensity": self.latest_state.grid_carbon_intensity
        }

    def get_weather(self) -> Dict[str, Any]:
        if not self.latest_state:
            return {"outdoor_temp": 25.0, "outdoor_humidity": 50.0}
        return {
            "outdoor_temp_c": self.latest_state.outdoor_temp,
            "outdoor_humidity_pct": self.latest_state.outdoor_humidity
        }

    def get_equipment_status(self) -> Dict[str, Any]:
        if not self.latest_state or not self.latest_state.telemetry:
            return {"status": "UNKNOWN"}
        t = self.latest_state.telemetry
        return {
            "ahu": {"status": t.ahu_status, "health_pct": t.ahu_health},
            "pump": {"status": t.pump_status, "health_pct": t.pump_health},
            "fan": {"status": t.fan_status, "health_pct": t.fan_health},
            "chiller": {"status": t.chiller_status, "health_pct": t.chiller_health},
            "total_power_kw": t.total_power_kw,
            "runtime_hours": t.cumulative_runtime_hours,
            "cycling_count": t.cycling_count
        }

    # --- Actuator Tools ---
    def set_hvac_setpoint(self, zone_id: str, temp_c: float) -> Dict[str, Any]:
        self.pending_action.zone_setpoints[zone_id] = temp_c
        return {"status": "SUCCESS", "zone_id": zone_id, "new_setpoint_c": temp_c}

    def set_airflow(self, zone_id: str, rate: float) -> Dict[str, Any]:
        self.pending_action.zone_airflows[zone_id] = rate
        return {"status": "SUCCESS", "zone_id": zone_id, "new_airflow": rate}

    def set_lighting(self, zone_id: str, level: float) -> Dict[str, Any]:
        self.pending_action.zone_lighting[zone_id] = level
        return {"status": "SUCCESS", "zone_id": zone_id, "new_lighting": level}

    def set_ventilation(self, rate: float) -> Dict[str, Any]:
        self.pending_action.ventilation_rate = rate
        return {"status": "SUCCESS", "new_ventilation_rate": rate}

    def switch_pump(self) -> Dict[str, Any]:
        self.pending_action.pump_switch_active = True
        return {"status": "SUCCESS", "pump_switch": True}
