"""
SentinelAI - Equipment Health Engine (Phase 4)
Computes real-time equipment Health Scores (0-100%), Stress Indices,
Remaining Useful Life (RUL) estimation in operating hours, Anomaly Detection,
and Predictive Maintenance Alerts for AHU, Pump, Fan, and Chiller.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from .models import (
    EquipmentType, AlertSeverity, EquipmentStressDetails,
    AnomalyDetectionResult, PredictiveMaintenanceAlert,
    AssetHealthReport, OverallBuildingHealthReport
)
from ..database.models import BuildingState

logger = logging.getLogger(__name__)

# Nominal equipment design lifespan (operating hours under normal rated conditions)
NOMINAL_LIFESPAN_HOURS = {
    EquipmentType.AHU: 50000.0,
    EquipmentType.CHILLER: 60000.0,
    EquipmentType.PUMP: 35000.0,
    EquipmentType.FAN: 40000.0,
}

class EquipmentHealthEngine:
    def __init__(self):
        # Current asset health state (percentage 0.0 to 100.0)
        self.health_scores: Dict[EquipmentType, float] = {
            EquipmentType.AHU: 98.0,
            EquipmentType.CHILLER: 92.0,
            EquipmentType.PUMP: 78.0,
            EquipmentType.FAN: 95.0,
        }

        self.statuses: Dict[EquipmentType, str] = {
            eq: "NORMAL" for eq in EquipmentType
        }

        self.overload_counts: Dict[EquipmentType, int] = {
            eq: 0 for eq in EquipmentType
        }

        self.prev_power_kw: float = 0.0
        self.prev_cycling_count: int = 0
        self.latest_report: Optional[OverallBuildingHealthReport] = None

    def evaluate_state(self, state: BuildingState) -> OverallBuildingHealthReport:
        """
        Evaluates current BuildingState telemetry, updates asset health scores,
        computes Stress Index & RUL, runs Anomaly Detection, and generates alerts.
        """
        telemetry = state.telemetry
        runtime_hours = telemetry.cumulative_runtime_hours if telemetry else 0.0
        cycling_count = telemetry.cycling_count if telemetry else 0
        power_kw = telemetry.total_power_kw if telemetry else 0.0

        # Detect power overload surge (> 25 kW)
        is_overloaded = power_kw > 25.0
        if is_overloaded:
            for eq in EquipmentType:
                self.overload_counts[eq] += 1

        # Calculate asset degradation & update health scores
        for eq in EquipmentType:
            # Baseline aging degradation
            degradation = 0.005  # -0.005% per step
            if is_overloaded:
                degradation += 0.2  # overload penalty
            if cycling_count > self.prev_cycling_count:
                degradation += 0.3 * (cycling_count - self.prev_cycling_count)  # cycling penalty

            self.health_scores[eq] = max(0.0, min(100.0, self.health_scores[eq] - degradation))

            # Status assignment
            if self.health_scores[eq] < 40.0:
                self.statuses[eq] = "CRITICAL"
            elif self.health_scores[eq] < 75.0:
                self.statuses[eq] = "DEGRADED"
            elif self.statuses[eq] != "REGENERATED":
                self.statuses[eq] = "NORMAL"

        self.prev_power_kw = power_kw
        self.prev_cycling_count = cycling_count

        # Build asset-level health reports
        asset_reports: Dict[str, AssetHealthReport] = {}
        all_anomalies: List[AnomalyDetectionResult] = []
        all_alerts: List[PredictiveMaintenanceAlert] = []

        for eq in EquipmentType:
            h_score = self.health_scores[eq]
            overloads = self.overload_counts[eq]

            # 1. Stress Index calculation (0.0 to 10.0+)
            stress_index = round(
                (runtime_hours * 0.001) + (cycling_count * 0.2) + (overloads * 0.5), 2
            )

            # 2. Remaining Useful Life (RUL) estimation in operating hours
            nominal_hours = NOMINAL_LIFESPAN_HOURS[eq]
            stress_factor = 1.0 + (0.1 * stress_index)
            rul_hours = round(max(0.0, (nominal_hours - runtime_hours) * (h_score / 100.0) / stress_factor), 1)

            # 3. Anomaly Detection
            eq_anomalies = self._detect_anomalies(eq, h_score, power_kw, cycling_count, overloads)
            all_anomalies.extend(eq_anomalies)

            # 4. Predictive Maintenance Alerts
            eq_alerts = self._generate_alerts(eq, h_score, stress_index, rul_hours, eq_anomalies)
            all_alerts.extend(eq_alerts)

            asset_reports[eq.value] = AssetHealthReport(
                equipment_type=eq,
                health_score=round(h_score, 1),
                status=self.statuses[eq],
                rul_hours=rul_hours,
                stress_index=stress_index,
                anomalies=eq_anomalies,
                active_alerts=eq_alerts
            )

        # Overall building health score (weighted average: Chiller 35%, AHU 25%, Pump 20%, Fan 20%)
        weights = {
            EquipmentType.CHILLER: 0.35,
            EquipmentType.AHU: 0.25,
            EquipmentType.PUMP: 0.20,
            EquipmentType.FAN: 0.20
        }
        overall_health = sum(self.health_scores[eq] * weights[eq] for eq in EquipmentType)

        report = OverallBuildingHealthReport(
            timestep=state.timestep,
            timestamp=time.time(),
            overall_health_score=round(overall_health, 1),
            assets=asset_reports,
            building_anomalies=all_anomalies,
            active_alerts=all_alerts
        )
        self.latest_report = report
        return report

    def apply_regeneration_switch(self, equipment_type: EquipmentType = EquipmentType.PUMP, boost_pct: float = 20.0):
        """Applies maintenance regeneration boost (e.g. pump switchover or fluid flushing)."""
        self.health_scores[equipment_type] = min(100.0, self.health_scores[equipment_type] + boost_pct)
        self.statuses[equipment_type] = "REGENERATED"
        logger.info(f"Health Engine: Applied {boost_pct}% maintenance regeneration boost to {equipment_type.value}.")

    def _detect_anomalies(
        self, eq: EquipmentType, health: float, power_kw: float, cycling_count: int, overloads: int
    ) -> List[AnomalyDetectionResult]:
        anomalies = []

        # Power surge anomaly
        if power_kw > 28.0:
            anomalies.append(AnomalyDetectionResult(
                is_anomaly=True,
                equipment_type=eq,
                anomaly_type="POWER_SPIKE_SURGE",
                anomaly_score=0.92,
                message=f"{eq.value} detected excessive electrical demand surge ({power_kw:.1f} kW > 28.0 kW)."
            ))

        # Rapid cycling anomaly
        if cycling_count >= 5:
            anomalies.append(AnomalyDetectionResult(
                is_anomaly=True,
                equipment_type=eq,
                anomaly_type="RAPID_CYCLING_STRESS",
                anomaly_score=0.88,
                message=f"{eq.value} experiencing high-frequency cycling ({cycling_count} start/stop transitions)."
            ))

        # Critical health degradation anomaly
        if health < 50.0:
            anomalies.append(AnomalyDetectionResult(
                is_anomaly=True,
                equipment_type=eq,
                anomaly_type="CRITICAL_HEALTH_DEGRADATION",
                anomaly_score=0.95,
                message=f"{eq.value} health score dropped below 50% threshold ({health:.1f}%)."
            ))

        return anomalies

    def _generate_alerts(
        self, eq: EquipmentType, health: float, stress_index: float, rul_hours: float, anomalies: List[AnomalyDetectionResult]
    ) -> List[PredictiveMaintenanceAlert]:
        alerts = []

        if health < 50.0:
            alerts.append(PredictiveMaintenanceAlert(
                equipment_type=eq,
                severity=AlertSeverity.CRITICAL,
                title=f"CRITICAL: {eq.value} Requires Immediate Overhaul",
                description=f"{eq.value} health is at {health:.1f}% with estimated RUL of only {rul_hours:.0f} operating hours.",
                suggested_action=f"Schedule urgent maintenance for {eq.value} and activate redundant switchover."
            ))
        elif health < 75.0:
            alerts.append(PredictiveMaintenanceAlert(
                equipment_type=eq,
                severity=AlertSeverity.WARNING,
                title=f"WARNING: {eq.value} Health Degraded",
                description=f"{eq.value} health is at {health:.1f}% (Stress Index: {stress_index}).",
                suggested_action=f"Inspect {eq.value} components and reduce thermal setpoint fluctuation."
            ))

        for anom in anomalies:
            if anom.anomaly_type == "POWER_SPIKE_SURGE":
                alerts.append(PredictiveMaintenanceAlert(
                    equipment_type=eq,
                    severity=AlertSeverity.WARNING,
                    title=f"POWER ANOMALY: {eq.value} High Electrical Demand",
                    description=anom.message,
                    suggested_action="Check electrical supply voltage and motor winding impedance."
                ))

        return alerts
