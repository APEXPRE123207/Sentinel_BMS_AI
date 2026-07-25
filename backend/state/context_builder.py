"""
SentinelAI - Rolling Context Builder
Maintains a rolling window of the previous N (default 10) control intervals
and constructs a compact summary to pass to the Agent Council LLM prompt.
"""
from collections import deque
from typing import Dict, Any, List
from ..database.models import BuildingState

class RollingContextBuilder:
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.history: deque[BuildingState] = deque(maxlen=window_size)

    def add_state(self, state: BuildingState):
        self.history.append(state)

    def build_context(self, current_state: BuildingState) -> Dict[str, Any]:
        """
        Builds current state representation + aggregated rolling trend summary.
        """
        # Current State breakdown
        zones_summary = {}
        for zone_id, z in current_state.zones.items():
            zones_summary[zone_id] = {
                "temp_c": round(z.temperature, 2),
                "setpoint_c": round(z.target_setpoint, 2),
                "humidity_pct": round(z.humidity, 1),
                "co2_ppm": round(z.co2, 0),
                "pmv": round(z.pmv, 2),
                "occupancy": z.occupancy,
                "airflow": round(z.airflow, 2),
                "lighting": round(z.lighting_level, 2)
            }

        equipment_summary = {}
        if current_state.telemetry:
            t = current_state.telemetry
            equipment_summary = {
                "ahu_health_pct": round(t.ahu_health, 1),
                "pump_health_pct": round(t.pump_health, 1),
                "fan_health_pct": round(t.fan_health, 1),
                "chiller_health_pct": round(t.chiller_health, 1),
                "power_kw": round(t.total_power_kw, 2),
                "runtime_hours": round(t.cumulative_runtime_hours, 1),
                "cycling_count": t.cycling_count
            }

        # Rolling trend calculation over history
        history_len = len(self.history)
        if history_len > 0:
            avg_outdoor = sum(s.outdoor_temp for s in self.history) / history_len
            total_energy = sum(s.total_energy_kwh for s in self.history)
            total_carbon = sum(s.carbon_emissions_kg for s in self.history)

            zone_temps = []
            zone_pmvs = []
            for s in self.history:
                for z in s.zones.values():
                    zone_temps.append(z.temperature)
                    zone_pmvs.append(z.pmv)

            min_temp = min(zone_temps) if zone_temps else 0.0
            max_temp = max(zone_temps) if zone_temps else 0.0
            avg_temp = sum(zone_temps) / len(zone_temps) if zone_temps else 0.0
            avg_pmv = sum(zone_pmvs) / len(zone_pmvs) if zone_pmvs else 0.0
        else:
            avg_outdoor = current_state.outdoor_temp
            total_energy = current_state.total_energy_kwh
            total_carbon = current_state.carbon_emissions_kg
            min_temp = max_temp = avg_temp = 22.0
            avg_pmv = 0.0

        rolling_summary = {
            "window_size": history_len,
            "avg_outdoor_temp_c": round(avg_outdoor, 2),
            "zone_min_temp_c": round(min_temp, 2),
            "zone_max_temp_c": round(max_temp, 2),
            "zone_avg_temp_c": round(avg_temp, 2),
            "avg_pmv": round(avg_pmv, 2),
            "rolling_energy_kwh": round(total_energy, 2),
            "rolling_carbon_kg": round(total_carbon, 2)
        }

        return {
            "timestep": current_state.timestep,
            "outdoor_temp_c": current_state.outdoor_temp,
            "outdoor_humidity_pct": current_state.outdoor_humidity,
            "zones": zones_summary,
            "equipment": equipment_summary,
            "rolling_trend_summary": rolling_summary
        }
