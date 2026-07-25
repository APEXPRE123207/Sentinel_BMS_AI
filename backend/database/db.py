"""
SentinelAI - SQLite Database Layer
Manages database initialization, schema creation, and structured data logging for simulation timesteps,
agent council decisions, safety validator logs, equipment health, and baseline comparison metrics.
"""
import sqlite3
import json
import os
from typing import Optional, List, Dict, Any
from .models import BuildingState, AgentCouncilDecision, ValidationResult, EquipmentTelemetry

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sentinel_ai.db")

import contextlib

class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table 1: BuildingState (Stores every simulation timestep)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS BuildingState (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                outdoor_temp REAL,
                outdoor_humidity REAL,
                grid_carbon_intensity REAL,
                total_energy_kwh REAL,
                carbon_emissions_kg REAL,
                zones_json TEXT,
                telemetry_json TEXT
            );
            """)

            # Table 2: AgentDecision (Stores every AI recommendation)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS AgentDecision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                energy_reasoning TEXT,
                comfort_reasoning TEXT,
                carbon_reasoning TEXT,
                health_reasoning TEXT,
                recommended_action_json TEXT,
                raw_response TEXT
            );
            """)

            # Table 3: ValidatorLog (Stores validation results)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ValidatorLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                is_valid INTEGER,
                attempt_number INTEGER,
                violated_rules_json TEXT,
                rejection_reason TEXT,
                used_fallback INTEGER,
                action_json TEXT,
                applied_action_json TEXT
            );
            """)

            # Table 4: EquipmentHealth (Stores historical health scores)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS EquipmentHealth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                ahu_health REAL,
                pump_health REAL,
                fan_health REAL,
                chiller_health REAL,
                ahu_status TEXT,
                pump_status TEXT,
                fan_status TEXT,
                chiller_status TEXT,
                total_power_kw REAL,
                cumulative_runtime_hours REAL,
                cycling_count INTEGER
            );
            """)

            # Table 5: BaselineMetrics (Stores baseline simulation outputs)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS BaselineMetrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                total_energy_kwh REAL,
                avg_pmv REAL,
                carbon_emissions_kg REAL,
                equipment_stress_score REAL
            );
            """)

            # Table 6: AISimulationMetrics (Stores AI-controlled simulation outputs)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS AISimulationMetrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestep INTEGER,
                total_energy_kwh REAL,
                avg_pmv REAL,
                carbon_emissions_kg REAL,
                equipment_stress_score REAL,
                energy_saved_pct REAL,
                carbon_reduced_pct REAL
            );
            """)

            conn.commit()

    def log_building_state(self, state: BuildingState):
        zones_data = {
            z_id: {
                "temperature": z.temperature,
                "target_setpoint": z.target_setpoint,
                "humidity": z.humidity,
                "co2": z.co2,
                "pmv": z.pmv,
                "occupancy": z.occupancy,
                "airflow": z.airflow,
                "lighting_level": z.lighting_level
            }
            for z_id, z in state.zones.items()
        }
        telemetry_data = state.telemetry.__dict__ if state.telemetry else {}

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO BuildingState (
                    timestamp, timestep, outdoor_temp, outdoor_humidity,
                    grid_carbon_intensity, total_energy_kwh, carbon_emissions_kg,
                    zones_json, telemetry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.timestamp, state.timestep, state.outdoor_temp, state.outdoor_humidity,
                state.grid_carbon_intensity, state.total_energy_kwh, state.carbon_emissions_kg,
                json.dumps(zones_data), json.dumps(telemetry_data)
            ))
            
            if state.telemetry:
                t = state.telemetry
                cursor.execute("""
                    INSERT INTO EquipmentHealth (
                        timestamp, timestep, ahu_health, pump_health, fan_health, chiller_health,
                        ahu_status, pump_status, fan_status, chiller_status,
                        total_power_kw, cumulative_runtime_hours, cycling_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.timestamp, state.timestep, t.ahu_health, t.pump_health, t.fan_health, t.chiller_health,
                    t.ahu_status, t.pump_status, t.fan_status, t.chiller_status,
                    t.total_power_kw, t.cumulative_runtime_hours, t.cycling_count
                ))

            conn.commit()

    def log_agent_decision(self, decision: AgentCouncilDecision):
        action_data = decision.recommended_action.__dict__
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO AgentDecision (
                    timestamp, timestep, energy_reasoning, comfort_reasoning,
                    carbon_reasoning, health_reasoning, recommended_action_json, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.timestamp, decision.timestep, decision.energy_reasoning,
                decision.comfort_reasoning, decision.carbon_reasoning, decision.health_reasoning,
                json.dumps(action_data), decision.raw_response
            ))
            conn.commit()

    def log_validation_result(self, timestep: int, timestamp: float, result: ValidationResult):
        action_data = result.action.__dict__
        applied_action_data = result.applied_action.__dict__ if result.applied_action else {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ValidatorLog (
                    timestamp, timestep, is_valid, attempt_number,
                    violated_rules_json, rejection_reason, used_fallback,
                    action_json, applied_action_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, timestep, 1 if result.is_valid else 0, result.attempt_number,
                json.dumps(result.violated_rules), result.rejection_reason, 1 if result.used_fallback else 0,
                json.dumps(action_data), json.dumps(applied_action_data)
            ))
            conn.commit()

    def log_baseline_metrics(self, timestep: int, timestamp: float, total_energy_kwh: float, avg_pmv: float, carbon_emissions_kg: float, equipment_stress_score: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO BaselineMetrics (
                    timestamp, timestep, total_energy_kwh, avg_pmv, carbon_emissions_kg, equipment_stress_score
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, timestep, total_energy_kwh, avg_pmv, carbon_emissions_kg, equipment_stress_score))
            conn.commit()

    def log_ai_simulation_metrics(
        self, timestep: int, timestamp: float, total_energy_kwh: float, avg_pmv: float,
        carbon_emissions_kg: float, equipment_stress_score: float, energy_saved_pct: float, carbon_reduced_pct: float
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO AISimulationMetrics (
                    timestamp, timestep, total_energy_kwh, avg_pmv, carbon_emissions_kg,
                    equipment_stress_score, energy_saved_pct, carbon_reduced_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, timestep, total_energy_kwh, avg_pmv, carbon_emissions_kg,
                equipment_stress_score, energy_saved_pct, carbon_reduced_pct
            ))
            conn.commit()

    def log_equipment_health_report(self, report):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            ahu = report.assets.get("AHU")
            pump = report.assets.get("PUMP")
            fan = report.assets.get("FAN")
            chiller = report.assets.get("CHILLER")

            cursor.execute("""
                INSERT INTO EquipmentHealth (
                    timestamp, timestep, ahu_health, pump_health, fan_health, chiller_health,
                    ahu_status, pump_status, fan_status, chiller_status,
                    total_power_kw, cumulative_runtime_hours, cycling_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.timestamp, report.timestep,
                ahu.health_score if ahu else 98.0,
                pump.health_score if pump else 78.0,
                fan.health_score if fan else 95.0,
                chiller.health_score if chiller else 92.0,
                ahu.status if ahu else "NORMAL",
                pump.status if pump else "NORMAL",
                fan.status if fan else "NORMAL",
                chiller.status if chiller else "NORMAL",
                0.0, 0.0, 0
            ))
            conn.commit()

    def get_latest_equipment_health(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM EquipmentHealth ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_baseline_metrics(self, timestep: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM BaselineMetrics WHERE timestep = ? ORDER BY id DESC LIMIT 1;", (timestep,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT * FROM BaselineMetrics ORDER BY ABS(timestep - ?) ASC LIMIT 1;", (timestep,))
                row = cursor.fetchone()
            return dict(row) if row else None


