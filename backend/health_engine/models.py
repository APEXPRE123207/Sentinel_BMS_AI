"""
SentinelAI - Equipment Health Engine Data Models (Phase 4)
Defines data structures for asset health scores, stress indices, RUL forecasts,
anomaly detection, and predictive maintenance alerts.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

class EquipmentType(str, Enum):
    AHU = "AHU"
    CHILLER = "CHILLER"
    PUMP = "PUMP"
    FAN = "FAN"

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    REGENERATED = "REGENERATED"

@dataclass
class EquipmentStressDetails:
    equipment_type: EquipmentType
    runtime_hours: float
    cycling_count: int
    overload_instances: int
    stress_index: float  # 0.0 to 10.0+ scale

@dataclass
class AnomalyDetectionResult:
    is_anomaly: bool
    equipment_type: EquipmentType
    anomaly_type: str  # e.g., "POWER_SPIKE", "RAPID_CYCLING", "THERMAL_OVERLOAD"
    anomaly_score: float  # 0.0 to 1.0 confidence score
    message: str

@dataclass
class PredictiveMaintenanceAlert:
    equipment_type: EquipmentType
    severity: AlertSeverity
    title: str
    description: str
    suggested_action: str

@dataclass
class AssetHealthReport:
    equipment_type: EquipmentType
    health_score: float            # 0.0% to 100.0%
    status: str                    # "NORMAL", "DEGRADED", "CRITICAL", "REGENERATED"
    rul_hours: float               # Remaining Useful Life in operating hours
    stress_index: float            # 0.0 to 10.0+
    anomalies: List[AnomalyDetectionResult] = field(default_factory=list)
    active_alerts: List[PredictiveMaintenanceAlert] = field(default_factory=list)

@dataclass
class OverallBuildingHealthReport:
    timestep: int
    timestamp: float
    overall_health_score: float   # Weighted average health across all assets
    assets: Dict[str, AssetHealthReport] = field(default_factory=dict)
    building_anomalies: List[AnomalyDetectionResult] = field(default_factory=list)
    active_alerts: List[PredictiveMaintenanceAlert] = field(default_factory=list)
