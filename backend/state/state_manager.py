"""
SentinelAI - State Manager
Acts as the single source of truth for the building state.
Reads building telemetry, zone states, weather, and equipment metrics,
stores them to SQLite, and supplies the unified state object downstream.
"""
import time
from typing import Dict, Any, Optional
from ..database.models import BuildingState, ZoneState, EquipmentTelemetry
from ..database.db import DatabaseManager

class StateManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_state: Optional[BuildingState] = None

    def update_state(
        self,
        timestep: int,
        outdoor_temp: float,
        outdoor_humidity: float,
        zones_data: Dict[str, Dict[str, Any]],
        equipment_data: Dict[str, Any],
        grid_carbon_intensity: float = 0.45,
        total_energy_kwh: float = 0.0,
        carbon_emissions_kg: float = 0.0
    ) -> BuildingState:
        """
        Creates a unified BuildingState instance, logs it atomically to SQLite,
        and returns the state object for downstream consumption (ContextBuilder, Agent Council, etc).
        """
        zones = {}
        for zone_id, z in zones_data.items():
            zones[zone_id] = ZoneState(
                zone_id=zone_id,
                temperature=z.get("temperature", 22.0),
                target_setpoint=z.get("target_setpoint", 22.0),
                humidity=z.get("humidity", 50.0),
                co2=z.get("co2", 400.0),
                pmv=z.get("pmv", 0.0),
                occupancy=z.get("occupancy", 0),
                airflow=z.get("airflow", 0.5),
                lighting_level=z.get("lighting_level", 1.0)
            )

        telemetry = EquipmentTelemetry(
            ahu_status=equipment_data.get("ahu_status", "NORMAL"),
            ahu_health=equipment_data.get("ahu_health", 98.0),
            pump_status=equipment_data.get("pump_status", "NORMAL"),
            pump_health=equipment_data.get("pump_health", 95.0),
            fan_status=equipment_data.get("fan_status", "NORMAL"),
            fan_health=equipment_data.get("fan_health", 96.0),
            chiller_status=equipment_data.get("chiller_status", "NORMAL"),
            chiller_health=equipment_data.get("chiller_health", 99.0),
            total_power_kw=equipment_data.get("total_power_kw", 15.0),
            cumulative_runtime_hours=equipment_data.get("cumulative_runtime_hours", 120.0),
            cycling_count=equipment_data.get("cycling_count", 4)
        )

        state = BuildingState(
            timestamp=time.time(),
            timestep=timestep,
            outdoor_temp=outdoor_temp,
            outdoor_humidity=outdoor_humidity,
            grid_carbon_intensity=grid_carbon_intensity,
            zones=zones,
            telemetry=telemetry,
            total_energy_kwh=total_energy_kwh,
            carbon_emissions_kg=carbon_emissions_kg
        )

        # Atomic persistence to SQLite
        self.db_manager.log_building_state(state)
        self.current_state = state

        return state
