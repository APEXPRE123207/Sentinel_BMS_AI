"""
SentinelAI - Core Data Models
Defines data structures for state, telemetry, agent decisions, validation, and equipment health.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

@dataclass
class ZoneState:
    zone_id: str
    temperature: float          # °C
    target_setpoint: float      # °C
    humidity: float             # %
    co2: float                  # ppm
    pmv: float                  # Predicted Mean Vote (-3 to +3)
    occupancy: int              # count
    airflow: float              # m³/s (0.1 to 1.0 fraction or flow)
    lighting_level: float       # 0.0 to 1.0

@dataclass
class EquipmentTelemetry:
    ahu_status: str             # "NORMAL", "WARNING", "DEGRADED", "OFF"
    ahu_health: float           # 0-100%
    pump_status: str
    pump_health: float          # 0-100%
    fan_status: str
    fan_health: float           # 0-100%
    chiller_status: str
    chiller_health: float       # 0-100%
    total_power_kw: float
    cumulative_runtime_hours: float
    cycling_count: int

@dataclass
class BuildingState:
    timestamp: float = field(default_factory=time.time)
    timestep: int = 0
    outdoor_temp: float = 25.0  # °C
    outdoor_humidity: float = 50.0 # %
    grid_carbon_intensity: float = 0.45 # kg CO2 per kWh
    zones: Dict[str, ZoneState] = field(default_factory=dict)
    telemetry: Optional[EquipmentTelemetry] = None
    total_energy_kwh: float = 0.0
    carbon_emissions_kg: float = 0.0

@dataclass
class ActionRecommendation:
    zone_setpoints: Dict[str, float] = field(default_factory=dict) # zone_id -> temp_c
    zone_airflows: Dict[str, float] = field(default_factory=dict)  # zone_id -> rate
    zone_lighting: Dict[str, float] = field(default_factory=dict)  # zone_id -> level
    ventilation_rate: Optional[float] = None
    pump_switch_active: bool = False

@dataclass
class AgentCouncilDecision:
    timestamp: float = field(default_factory=time.time)
    timestep: int = 0
    energy_reasoning: str = ""
    comfort_reasoning: str = ""
    carbon_reasoning: str = ""
    health_reasoning: str = ""
    recommended_action: ActionRecommendation = field(default_factory=ActionRecommendation)
    raw_response: str = ""

@dataclass
class RuleViolation:
    """Represents a single safety rule violation with fix guidance for LLM retry."""
    rule_name: str
    category: str        # "COMFORT", "EQUIPMENT", "PHYSICAL", "RATE_LIMIT"
    severity: str        # "WARNING", "CRITICAL"
    message: str
    suggested_fix: str   # Human-readable hint for LLM retry

@dataclass
class ValidationResult:
    is_valid: bool
    violated_rules: List[str] = field(default_factory=list)
    rule_violations: List[RuleViolation] = field(default_factory=list)
    rejection_reason: str = ""
    attempt_number: int = 1
    action: ActionRecommendation = field(default_factory=ActionRecommendation)
    applied_action: Optional[ActionRecommendation] = None
    used_fallback: bool = False
