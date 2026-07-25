"""
SentinelAI - Phase 2 Safety Rules Test Suite
Tests each modular safety rule individually and validates structured feedback generation.
"""
import os
import json
import tempfile
import unittest
from backend.database.models import (
    BuildingState, ZoneState, EquipmentTelemetry,
    ActionRecommendation, RuleViolation
)
from backend.validator.rules import (
    SetpointRangeRule, AirflowRangeRule, LightingRangeRule,
    SetpointRateOfChangeRule, PMVComfortRule, CO2VentilationRule,
    ChillerMinRuntimeRule, FanStaticPressureRule, PumpHealthRule,
    get_default_rules
)
from backend.validator.safety_validator import SafetyValidator

def _make_building_state(
    zones=None, pmv_override=None, co2_override=None,
    fan_health=95.0, pump_health=85.0,
    runtime_hours=50.0, cycling_count=4
):
    """Helper to create a BuildingState for testing."""
    if zones is None:
        zones = {
            "Office": ZoneState(
                zone_id="Office", temperature=23.0, target_setpoint=22.0,
                humidity=50.0, co2=co2_override or 420.0,
                pmv=pmv_override if pmv_override is not None else 0.2,
                occupancy=5, airflow=0.5, lighting_level=0.8
            )
        }
    return BuildingState(
        timestep=1, outdoor_temp=25.0, outdoor_humidity=50.0,
        zones=zones,
        telemetry=EquipmentTelemetry(
            ahu_status="NORMAL", ahu_health=98.0,
            pump_status="NORMAL", pump_health=pump_health,
            fan_status="NORMAL", fan_health=fan_health,
            chiller_status="NORMAL", chiller_health=92.0,
            total_power_kw=15.0,
            cumulative_runtime_hours=runtime_hours,
            cycling_count=cycling_count
        ),
        total_energy_kwh=5.0, carbon_emissions_kg=2.25
    )

class TestSafetyRules(unittest.TestCase):

    def test_setpoint_range_rule_valid(self):
        rule = SetpointRangeRule(min_c=19.0, max_c=26.0)
        action = ActionRecommendation(zone_setpoints={"Office": 22.0})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 0)

    def test_setpoint_range_rule_below_min(self):
        rule = SetpointRangeRule(min_c=19.0, max_c=26.0)
        action = ActionRecommendation(zone_setpoints={"Office": 15.0})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "SetpointRange")
        self.assertEqual(violations[0].severity, "CRITICAL")
        self.assertIn("15.0°C", violations[0].message)
        self.assertIn("19.0°C", violations[0].suggested_fix)

    def test_setpoint_range_rule_above_max(self):
        rule = SetpointRangeRule(min_c=19.0, max_c=26.0)
        action = ActionRecommendation(zone_setpoints={"Office": 30.0})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "CRITICAL")

    def test_airflow_range_rule_valid(self):
        rule = AirflowRangeRule()
        action = ActionRecommendation(zone_airflows={"Office": 0.5})
        self.assertEqual(len(rule.evaluate(action)), 0)

    def test_airflow_range_rule_below_min(self):
        rule = AirflowRangeRule(min_flow=0.1, max_flow=1.0)
        action = ActionRecommendation(zone_airflows={"Office": 0.05})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "AirflowRange")

    def test_lighting_range_rule_valid(self):
        rule = LightingRangeRule()
        action = ActionRecommendation(zone_lighting={"Office": 0.5})
        self.assertEqual(len(rule.evaluate(action)), 0)

    def test_lighting_range_rule_negative(self):
        rule = LightingRangeRule()
        action = ActionRecommendation(zone_lighting={"Office": -0.1})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "WARNING")

    def test_lighting_range_rule_above_max(self):
        rule = LightingRangeRule()
        action = ActionRecommendation(zone_lighting={"Office": 1.5})
        violations = rule.evaluate(action)
        self.assertEqual(len(violations), 1)

    def test_setpoint_rate_of_change_valid(self):
        rule = SetpointRateOfChangeRule(max_change_per_step=2.5)
        action = ActionRecommendation(zone_setpoints={"Office": 22.0})
        violations = rule.evaluate(action, current_setpoints={"Office": 21.0})
        self.assertEqual(len(violations), 0)

    def test_setpoint_rate_of_change_exceeded(self):
        rule = SetpointRateOfChangeRule(max_change_per_step=2.5)
        action = ActionRecommendation(zone_setpoints={"Office": 26.0})
        violations = rule.evaluate(action, current_setpoints={"Office": 22.0})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "SetpointRateOfChange")
        self.assertEqual(violations[0].category, "RATE_LIMIT")

    def test_setpoint_rate_of_change_no_current(self):
        rule = SetpointRateOfChangeRule(max_change_per_step=2.5)
        action = ActionRecommendation(zone_setpoints={"Office": 30.0})
        violations = rule.evaluate(action, current_setpoints=None)
        self.assertEqual(len(violations), 0)

    def test_pmv_comfort_rule_valid(self):
        rule = PMVComfortRule()
        action = ActionRecommendation(zone_setpoints={"Office": 22.0})
        state = _make_building_state(pmv_override=0.2)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_pmv_comfort_rule_too_warm_worsening(self):
        rule = PMVComfortRule()
        action = ActionRecommendation(zone_setpoints={"Office": 23.0})
        state = _make_building_state(pmv_override=0.8)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "PMVComfort")
        self.assertEqual(violations[0].category, "COMFORT")
        self.assertIn("PMV is 0.8", violations[0].message)

    def test_pmv_comfort_rule_too_warm_improving(self):
        rule = PMVComfortRule()
        action = ActionRecommendation(zone_setpoints={"Office": 21.0})
        state = _make_building_state(pmv_override=0.8)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_pmv_comfort_rule_too_cold_worsening(self):
        rule = PMVComfortRule()
        action = ActionRecommendation(zone_setpoints={"Office": 20.0})
        state = _make_building_state(pmv_override=-0.8)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 1)
        self.assertIn("worsening thermal comfort", violations[0].message)

    def test_pmv_comfort_rule_no_building_state(self):
        rule = PMVComfortRule()
        action = ActionRecommendation(zone_setpoints={"Office": 22.0})
        violations = rule.evaluate(action, building_state=None)
        self.assertEqual(len(violations), 0)

    def test_co2_ventilation_rule_high_co2_low_airflow(self):
        rule = CO2VentilationRule(co2_threshold_ppm=1000.0, min_airflow_high_co2=0.4)
        action = ActionRecommendation(zone_airflows={"Office": 0.2})
        state = _make_building_state(co2_override=1200.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "CO2Ventilation")
        self.assertIn("1200", violations[0].message)

    def test_co2_ventilation_rule_high_co2_adequate_airflow(self):
        rule = CO2VentilationRule(co2_threshold_ppm=1000.0, min_airflow_high_co2=0.4)
        action = ActionRecommendation(zone_airflows={"Office": 0.5})
        state = _make_building_state(co2_override=1200.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_co2_ventilation_rule_normal_co2(self):
        rule = CO2VentilationRule()
        action = ActionRecommendation(zone_airflows={"Office": 0.1})
        state = _make_building_state(co2_override=500.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_chiller_min_runtime_rule_safe(self):
        rule = ChillerMinRuntimeRule(min_runtime_hours=0.167, max_setpoint_delta=1.5)
        action = ActionRecommendation(zone_setpoints={"Office": 24.0})
        state = _make_building_state(runtime_hours=50.5, cycling_count=4)
        violations = rule.evaluate(action, building_state=state, current_setpoints={"Office": 22.0})
        self.assertEqual(len(violations), 0)

    def test_chiller_min_runtime_rule_rapid_cycling(self):
        rule = ChillerMinRuntimeRule(min_runtime_hours=0.167, max_setpoint_delta=1.5)
        action = ActionRecommendation(zone_setpoints={"Office": 24.0})
        state = _make_building_state(runtime_hours=50.05, cycling_count=4)
        violations = rule.evaluate(action, building_state=state, current_setpoints={"Office": 22.0})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "ChillerMinRuntime")

    def test_fan_static_pressure_rule_healthy_fan(self):
        rule = FanStaticPressureRule(fan_health_threshold=70.0, max_airflow_degraded=0.85)
        action = ActionRecommendation(zone_airflows={"Office": 0.95})
        state = _make_building_state(fan_health=95.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_fan_static_pressure_rule_degraded_fan_high_airflow(self):
        rule = FanStaticPressureRule(fan_health_threshold=70.0, max_airflow_degraded=0.85)
        action = ActionRecommendation(zone_airflows={"Office": 0.9})
        state = _make_building_state(fan_health=60.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_name, "FanStaticPressure")
        self.assertEqual(violations[0].category, "EQUIPMENT")

    def test_fan_static_pressure_rule_degraded_fan_safe_airflow(self):
        rule = FanStaticPressureRule(fan_health_threshold=70.0, max_airflow_degraded=0.85)
        action = ActionRecommendation(zone_airflows={"Office": 0.5})
        state = _make_building_state(fan_health=60.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_pump_health_rule_healthy(self):
        rule = PumpHealthRule(critical_health_threshold=50.0)
        action = ActionRecommendation(pump_switch_active=False)
        state = _make_building_state(pump_health=85.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_pump_health_rule_critical_no_switch(self):
        rule = PumpHealthRule(critical_health_threshold=50.0)
        action = ActionRecommendation(pump_switch_active=False)
        state = _make_building_state(pump_health=40.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "CRITICAL")
        self.assertIn("pump_switch_active", violations[0].suggested_fix)

    def test_pump_health_rule_critical_with_switch(self):
        rule = PumpHealthRule(critical_health_threshold=50.0)
        action = ActionRecommendation(pump_switch_active=True)
        state = _make_building_state(pump_health=40.0)
        violations = rule.evaluate(action, building_state=state)
        self.assertEqual(len(violations), 0)

    def test_validator_all_rules_pass(self):
        validator = SafetyValidator()
        action = ActionRecommendation(
            zone_setpoints={"Office": 22.0},
            zone_airflows={"Office": 0.5},
            zone_lighting={"Office": 0.8}
        )
        state = _make_building_state()
        result = validator.validate(action, building_state=state)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.rule_violations), 0)

    def test_validator_multiple_violations(self):
        validator = SafetyValidator()
        action = ActionRecommendation(
            zone_setpoints={"Office": 15.0},
            zone_airflows={"Office": 0.05},
            zone_lighting={"Office": 1.5}
        )
        result = validator.validate(action, attempt_number=1)
        self.assertFalse(result.is_valid)
        self.assertGreaterEqual(len(result.rule_violations), 3)

    def test_structured_feedback_generation(self):
        validator = SafetyValidator()
        action = ActionRecommendation(
            zone_setpoints={"Office": 15.0},
            zone_airflows={"Office": 0.05}
        )
        result = validator.validate(action, attempt_number=1)
        feedback = validator.build_feedback_prompt(result)

        self.assertIn("SAFETY VALIDATOR REJECTION", feedback)
        self.assertIn("SetpointRange", feedback)
        self.assertIn("AirflowRange", feedback)
        self.assertIn("FIX:", feedback)
        self.assertIn("PHYSICAL", feedback)

    def test_structured_feedback_empty_on_valid(self):
        validator = SafetyValidator()
        action = ActionRecommendation(
            zone_setpoints={"Office": 22.0},
            zone_airflows={"Office": 0.5}
        )
        result = validator.validate(action)
        feedback = validator.build_feedback_prompt(result)
        self.assertEqual(feedback, "")

    def test_lkg_serialization_roundtrip(self):
        validator = SafetyValidator()
        good_action = ActionRecommendation(
            zone_setpoints={"Office": 21.5, "Lobby": 23.0},
            zone_airflows={"Office": 0.6, "Lobby": 0.4},
            zone_lighting={"Office": 0.9, "Lobby": 0.5},
            ventilation_rate=0.5,
            pump_switch_active=False
        )
        validator.validate(good_action, attempt_number=1)

        lkg_json = validator.serialize_lkg()
        parsed = json.loads(lkg_json)
        self.assertEqual(parsed["zone_setpoints"]["Office"], 21.5)

        validator2 = SafetyValidator()
        validator2.deserialize_lkg(lkg_json)
        self.assertEqual(validator2.last_known_good_action.zone_setpoints["Office"], 21.5)
        self.assertEqual(validator2.last_known_good_action.zone_airflows["Lobby"], 0.4)

    def test_get_default_rules_count(self):
        rules = get_default_rules()
        self.assertEqual(len(rules), 9)

if __name__ == "__main__":
    unittest.main()
