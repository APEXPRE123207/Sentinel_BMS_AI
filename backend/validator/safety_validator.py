"""
SentinelAI - Safety Validator (v2.1 — Phase 2)
Modular rule-based safety validation engine.
Protects building physical infrastructure and occupant comfort.
Supports self-correcting retry loop with structured LLM feedback and
Last-Known-Good (LKG) fallback recovery with JSON serialization.
"""
import json
import copy
import logging
from typing import Dict, Any, List, Optional
from ..database.models import (
    ActionRecommendation, ValidationResult, BuildingState, RuleViolation
)
from .rules import SafetyRule, get_default_rules

logger = logging.getLogger(__name__)


class SafetyValidator:
    def __init__(
        self,
        rules: Optional[List[SafetyRule]] = None,
        # Legacy constructor params kept for backward compatibility
        min_setpoint_c: float = 19.0,
        max_setpoint_c: float = 26.0,
        min_airflow: float = 0.1,
        max_airflow: float = 1.0,
        max_setpoint_change_per_step: float = 2.5
    ):
        if rules is not None:
            self.rules = rules
        else:
            self.rules = get_default_rules()

        self.last_known_good_action: ActionRecommendation = self._default_lkg_action()

    def _default_lkg_action(self) -> ActionRecommendation:
        return ActionRecommendation(
            zone_setpoints={"Office": 22.0, "ConferenceRoom": 22.0, "Lobby": 23.0},
            zone_airflows={"Office": 0.5, "ConferenceRoom": 0.5, "Lobby": 0.4},
            zone_lighting={"Office": 0.8, "ConferenceRoom": 0.8, "Lobby": 0.5},
            ventilation_rate=0.5,
            pump_switch_active=False
        )

    def validate(
        self,
        action: ActionRecommendation,
        building_state: Optional[BuildingState] = None,
        attempt_number: int = 1,
        current_setpoints: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        """
        Evaluate all registered safety rules against the proposed action.
        Returns a ValidationResult with structured violations and feedback.
        """
        all_violations: List[RuleViolation] = []

        for rule in self.rules:
            violations = rule.evaluate(
                action=action,
                building_state=building_state,
                current_setpoints=current_setpoints
            )
            all_violations.extend(violations)

        # Build legacy violated_rules list (backward compatible)
        violated_rule_messages = [v.message for v in all_violations]
        is_valid = len(all_violations) == 0

        if is_valid:
            # Update Last Known Good action
            self.last_known_good_action = copy.deepcopy(action)
            return ValidationResult(
                is_valid=True,
                attempt_number=attempt_number,
                action=action,
                applied_action=action,
                used_fallback=False,
                rule_violations=[]
            )

        # Build structured rejection reason
        rejection_reason = " | ".join(violated_rule_messages)

        return ValidationResult(
            is_valid=False,
            violated_rules=violated_rule_messages,
            rule_violations=all_violations,
            rejection_reason=rejection_reason,
            attempt_number=attempt_number,
            action=action,
            applied_action=self.last_known_good_action if attempt_number >= 2 else None,
            used_fallback=(attempt_number >= 2)
        )

    def build_feedback_prompt(self, result: ValidationResult) -> str:
        """
        Generate a structured feedback prompt for LLM retry.
        Groups violations by category and includes suggested fixes.
        """
        if result.is_valid:
            return ""

        lines = ["[SAFETY VALIDATOR REJECTION — Correct the following violations:]", ""]

        # Group violations by category
        categories: Dict[str, List[RuleViolation]] = {}
        for v in result.rule_violations:
            categories.setdefault(v.category, []).append(v)

        for category, violations in categories.items():
            lines.append(f"## {category} Violations")
            for v in violations:
                lines.append(f"  - [{v.severity}] {v.rule_name}: {v.message}")
                lines.append(f"    FIX: {v.suggested_fix}")
            lines.append("")

        lines.append("Adjust your recommended_action JSON to satisfy ALL safety constraints above.")
        return "\n".join(lines)

    # --- LKG Serialization ---

    def serialize_lkg(self) -> str:
        """Serialize Last-Known-Good action to JSON string for persistence."""
        lkg = self.last_known_good_action
        return json.dumps({
            "zone_setpoints": lkg.zone_setpoints,
            "zone_airflows": lkg.zone_airflows,
            "zone_lighting": lkg.zone_lighting,
            "ventilation_rate": lkg.ventilation_rate,
            "pump_switch_active": lkg.pump_switch_active
        }, indent=2)

    def deserialize_lkg(self, data: str):
        """Restore Last-Known-Good action from JSON string."""
        parsed = json.loads(data)
        self.last_known_good_action = ActionRecommendation(
            zone_setpoints=parsed.get("zone_setpoints", {}),
            zone_airflows=parsed.get("zone_airflows", {}),
            zone_lighting=parsed.get("zone_lighting", {}),
            ventilation_rate=parsed.get("ventilation_rate", 0.5),
            pump_switch_active=parsed.get("pump_switch_active", False)
        )
