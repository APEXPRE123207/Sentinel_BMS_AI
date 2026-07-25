"""
SentinelAI - Modular Safety Rules (Phase 2)
Each rule is a self-contained class that evaluates a specific safety concern
and returns structured RuleViolation objects with suggested fixes for LLM retry.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..database.models import (
    ActionRecommendation, BuildingState, RuleViolation
)


class SafetyRule(ABC):
    """Base class for all safety rules."""
    name: str = "BaseRule"
    category: str = "PHYSICAL"  # COMFORT, EQUIPMENT, PHYSICAL, RATE_LIMIT

    @abstractmethod
    def evaluate(
        self,
        action: ActionRecommendation,
        building_state: Optional[BuildingState] = None,
        current_setpoints: Optional[Dict[str, float]] = None
    ) -> List[RuleViolation]:
        """Evaluate the action and return a list of violations (empty if valid)."""
        ...


# ---------------------------------------------------------------------------
# PHYSICAL RULES
# ---------------------------------------------------------------------------

class SetpointRangeRule(SafetyRule):
    """Enforces absolute setpoint temperature bounds."""
    name = "SetpointRange"
    category = "PHYSICAL"

    def __init__(self, min_c: float = 19.0, max_c: float = 26.0):
        self.min_c = min_c
        self.max_c = max_c

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        for z_id, temp_c in action.zone_setpoints.items():
            if temp_c < self.min_c:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="CRITICAL",
                    message=f"Zone {z_id} setpoint {temp_c}°C is below minimum safe limit ({self.min_c}°C)",
                    suggested_fix=f"Increase Zone {z_id} setpoint to at least {self.min_c}°C"
                ))
            elif temp_c > self.max_c:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="CRITICAL",
                    message=f"Zone {z_id} setpoint {temp_c}°C exceeds maximum safe limit ({self.max_c}°C)",
                    suggested_fix=f"Reduce Zone {z_id} setpoint to at most {self.max_c}°C"
                ))
        return violations


class AirflowRangeRule(SafetyRule):
    """Enforces absolute airflow bounds."""
    name = "AirflowRange"
    category = "PHYSICAL"

    def __init__(self, min_flow: float = 0.1, max_flow: float = 1.0):
        self.min_flow = min_flow
        self.max_flow = max_flow

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        for z_id, flow in action.zone_airflows.items():
            if flow < self.min_flow:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="CRITICAL",
                    message=f"Zone {z_id} airflow {flow} is below minimum ventilation limit ({self.min_flow})",
                    suggested_fix=f"Increase Zone {z_id} airflow to at least {self.min_flow}"
                ))
            elif flow > self.max_flow:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="CRITICAL",
                    message=f"Zone {z_id} airflow {flow} exceeds duct capacity limit ({self.max_flow})",
                    suggested_fix=f"Reduce Zone {z_id} airflow to at most {self.max_flow}"
                ))
        return violations


class LightingRangeRule(SafetyRule):
    """Enforces lighting level bounds (0.0 to 1.0)."""
    name = "LightingRange"
    category = "PHYSICAL"

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        for z_id, level in action.zone_lighting.items():
            if level < 0.0:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="WARNING",
                    message=f"Zone {z_id} lighting level {level} is negative",
                    suggested_fix=f"Set Zone {z_id} lighting to at least 0.0"
                ))
            elif level > 1.0:
                violations.append(RuleViolation(
                    rule_name=self.name, category=self.category, severity="WARNING",
                    message=f"Zone {z_id} lighting level {level} exceeds maximum (1.0)",
                    suggested_fix=f"Reduce Zone {z_id} lighting to at most 1.0"
                ))
        return violations


# ---------------------------------------------------------------------------
# RATE LIMIT RULES
# ---------------------------------------------------------------------------

class SetpointRateOfChangeRule(SafetyRule):
    """Limits how fast setpoints can change between consecutive timesteps."""
    name = "SetpointRateOfChange"
    category = "RATE_LIMIT"

    def __init__(self, max_change_per_step: float = 2.5):
        self.max_change = max_change_per_step

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not current_setpoints:
            return violations
        for z_id, temp_c in action.zone_setpoints.items():
            if z_id in current_setpoints:
                diff = abs(temp_c - current_setpoints[z_id])
                if diff > self.max_change:
                    violations.append(RuleViolation(
                        rule_name=self.name, category=self.category, severity="CRITICAL",
                        message=f"Zone {z_id} setpoint change of {round(diff, 2)}°C exceeds max rate of change ({self.max_change}°C/step)",
                        suggested_fix=f"Limit Zone {z_id} setpoint change to within {self.max_change}°C of current value ({current_setpoints[z_id]}°C)"
                    ))
        return violations


# ---------------------------------------------------------------------------
# COMFORT RULES
# ---------------------------------------------------------------------------

class PMVComfortRule(SafetyRule):
    """
    Rejects actions that worsen PMV beyond comfort bounds.
    PMV should stay within [-0.5, +0.5] for acceptable thermal comfort.
    Triggers when a zone's PMV is already outside bounds AND the proposed
    setpoint moves it further from the comfortable range.
    """
    name = "PMVComfort"
    category = "COMFORT"

    def __init__(self, pmv_lower: float = -0.5, pmv_upper: float = 0.5):
        self.pmv_lower = pmv_lower
        self.pmv_upper = pmv_upper

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not building_state:
            return violations

        for z_id, zone in building_state.zones.items():
            if z_id not in action.zone_setpoints:
                continue

            # Skip during EnergyPlus warmup period — zone temp reads as 0.0
            # PMV clamped to -3.0 from 0°C is a false reading, not a real comfort issue
            if zone.temperature == 0.0 or zone.temperature < 5.0:
                continue

            proposed_setpoint = action.zone_setpoints[z_id]

            if zone.pmv > self.pmv_upper:
                # Zone is too warm — setpoint should decrease or stay; raising it worsens comfort
                if proposed_setpoint > zone.target_setpoint:
                    violations.append(RuleViolation(
                        rule_name=self.name, category=self.category, severity="WARNING",
                        message=f"Zone {z_id} PMV is {zone.pmv} (>{self.pmv_upper}), but setpoint is increasing from {zone.target_setpoint}°C to {proposed_setpoint}°C, worsening thermal comfort",
                        suggested_fix=f"Lower Zone {z_id} setpoint to {zone.target_setpoint}°C or below to improve PMV"
                    ))
            elif zone.pmv < self.pmv_lower:
                # Zone is too cold — setpoint should increase or stay; lowering it worsens comfort
                if proposed_setpoint < zone.target_setpoint:
                    violations.append(RuleViolation(
                        rule_name=self.name, category=self.category, severity="WARNING",
                        message=f"Zone {z_id} PMV is {zone.pmv} (<{self.pmv_lower}), but setpoint is decreasing from {zone.target_setpoint}°C to {proposed_setpoint}°C, worsening thermal comfort",
                        suggested_fix=f"Raise Zone {z_id} setpoint to {zone.target_setpoint}°C or above to improve PMV"
                    ))
        return violations


class CO2VentilationRule(SafetyRule):
    """
    Ensures adequate ventilation when CO₂ concentration is high.
    If CO₂ > threshold, airflow must be at least the minimum ventilation rate.
    """
    name = "CO2Ventilation"
    category = "COMFORT"

    def __init__(self, co2_threshold_ppm: float = 1000.0, min_airflow_high_co2: float = 0.4):
        self.co2_threshold = co2_threshold_ppm
        self.min_airflow = min_airflow_high_co2

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not building_state:
            return violations

        for z_id, zone in building_state.zones.items():
            if zone.co2 > self.co2_threshold:
                proposed_airflow = action.zone_airflows.get(z_id)
                if proposed_airflow is not None and proposed_airflow < self.min_airflow:
                    violations.append(RuleViolation(
                        rule_name=self.name, category=self.category, severity="CRITICAL",
                        message=f"Zone {z_id} CO₂ is {zone.co2} ppm (>{self.co2_threshold}), but airflow is only {proposed_airflow} (minimum {self.min_airflow} required)",
                        suggested_fix=f"Increase Zone {z_id} airflow to at least {self.min_airflow} to dilute CO₂"
                    ))
        return violations


# ---------------------------------------------------------------------------
# EQUIPMENT RULES
# ---------------------------------------------------------------------------

class ChillerMinRuntimeRule(SafetyRule):
    """
    Prevents rapid chiller cycling by enforcing a minimum runtime window.
    If the chiller has been running for less than the minimum runtime (in hours)
    and a significant setpoint change is requested, block it.
    """
    name = "ChillerMinRuntime"
    category = "EQUIPMENT"

    def __init__(self, min_runtime_hours: float = 0.167, max_setpoint_delta: float = 1.5):
        # 0.167 hours ≈ 10 minutes
        self.min_runtime_hours = min_runtime_hours
        self.max_setpoint_delta = max_setpoint_delta

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not building_state or not building_state.telemetry:
            return violations
        if not current_setpoints:
            return violations

        t = building_state.telemetry
        # Check if chiller runtime within the current cycle is below minimum
        # Using cycling_count > 0 and fractional runtime as a proxy
        runtime_in_current_cycle = t.cumulative_runtime_hours % 1.0  # fractional hour within last hour
        if runtime_in_current_cycle < self.min_runtime_hours and t.cycling_count > 0:
            for z_id, temp_c in action.zone_setpoints.items():
                if z_id in current_setpoints:
                    delta = abs(temp_c - current_setpoints[z_id])
                    if delta > self.max_setpoint_delta:
                        violations.append(RuleViolation(
                            rule_name=self.name, category=self.category, severity="WARNING",
                            message=f"Chiller has run only {round(runtime_in_current_cycle * 60, 1)} min in current cycle. Zone {z_id} setpoint change of {round(delta, 2)}°C may cause rapid chiller cycling",
                            suggested_fix=f"Limit Zone {z_id} setpoint change to within {self.max_setpoint_delta}°C or wait for chiller to complete minimum runtime"
                        ))
        return violations


class FanStaticPressureRule(SafetyRule):
    """
    Prevents excessive airflow demand when fan health is degraded.
    High airflow on a degraded fan increases static pressure beyond safe limits.
    """
    name = "FanStaticPressure"
    category = "EQUIPMENT"

    def __init__(self, fan_health_threshold: float = 70.0, max_airflow_degraded: float = 0.85):
        self.health_threshold = fan_health_threshold
        self.max_airflow = max_airflow_degraded

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not building_state or not building_state.telemetry:
            return violations

        fan_health = building_state.telemetry.fan_health
        if fan_health < self.health_threshold:
            for z_id, flow in action.zone_airflows.items():
                if flow > self.max_airflow:
                    violations.append(RuleViolation(
                        rule_name=self.name, category=self.category, severity="WARNING",
                        message=f"Fan health is {fan_health}% (<{self.health_threshold}%). Zone {z_id} airflow {flow} exceeds safe limit ({self.max_airflow}) for degraded fan",
                        suggested_fix=f"Reduce Zone {z_id} airflow to at most {self.max_airflow} while fan health is below {self.health_threshold}%"
                    ))
        return violations


class PumpHealthRule(SafetyRule):
    """
    Forces pump rotation when pump health drops below critical threshold.
    If pump health is critically low and pump_switch_active is not set, flag violation.
    """
    name = "PumpHealth"
    category = "EQUIPMENT"

    def __init__(self, critical_health_threshold: float = 50.0):
        self.critical_threshold = critical_health_threshold

    def evaluate(self, action, building_state=None, current_setpoints=None):
        violations: List[RuleViolation] = []
        if not building_state or not building_state.telemetry:
            return violations

        pump_health = building_state.telemetry.pump_health
        if pump_health < self.critical_threshold and not action.pump_switch_active:
            violations.append(RuleViolation(
                rule_name=self.name, category=self.category, severity="CRITICAL",
                message=f"Pump health is critically low ({pump_health}% < {self.critical_threshold}%) but pump_switch_active is False",
                suggested_fix=f"Set pump_switch_active to True to rotate pump and prevent equipment failure"
            ))
        return violations


# ---------------------------------------------------------------------------
# DEFAULT RULE SET
# ---------------------------------------------------------------------------

def get_default_rules() -> List[SafetyRule]:
    """Returns the standard set of safety rules for SentinelAI."""
    return [
        # Physical bounds
        SetpointRangeRule(min_c=19.0, max_c=26.0),
        AirflowRangeRule(min_flow=0.1, max_flow=1.0),
        LightingRangeRule(),
        # Rate limits
        SetpointRateOfChangeRule(max_change_per_step=2.5),
        # Comfort
        PMVComfortRule(pmv_lower=-0.5, pmv_upper=0.5),
        CO2VentilationRule(co2_threshold_ppm=1000.0, min_airflow_high_co2=0.4),
        # Equipment protection
        ChillerMinRuntimeRule(),
        FanStaticPressureRule(fan_health_threshold=70.0, max_airflow_degraded=0.85),
        PumpHealthRule(critical_health_threshold=50.0),
    ]
