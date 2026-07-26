"""
SentinelAI - FastAPI REST API & Dashboard Service (Phase 5)
Provides REST endpoints for live telemetry, Agent Council decisions,
Safety Validator log streams, Equipment Health diagnostics, and Baseline comparison metrics.
Serves the interactive BMS Web Control Dashboard.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..database.db import DatabaseManager
from ..run_loop import SentinelAIControlLoop
from ..building.dual_runner import DualSimulationRunner
from ..health_engine.models import EquipmentType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SentinelAI-API")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do NOT create control_loop here — it starts EnergyPlus which blocks.
    # Instead, lazy-initialize on first /api/control/step call.
    logger.info("FastAPI Backend Service initialized. Dashboard ready at http://127.0.0.1:8000")
    logger.info("Click '▶ Execute Step' or '▶ Play Day' in the dashboard to start the simulation.")
    yield

app = FastAPI(
    title="SentinelAI BMS Control API",
    description="Autonomous Cyber-Physical Building Intelligence & Decision Dashboard",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration Endpoint ──
from pydantic import BaseModel
class ConfigUpdate(BaseModel):
    month: int
    day_of_week: str
    occupants: int

@app.post("/api/config")
def update_config(config: ConfigUpdate):
    """Updates run_config.json with new parameters and resets the simulation."""
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "..", "..", "run_config.json")
    
    current_cfg = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            current_cfg = json.load(f)
            
    if "simulation_start_date" not in current_cfg:
        current_cfg["simulation_start_date"] = {"day": 7}
    current_cfg["simulation_start_date"]["month"] = config.month
    current_cfg["day_of_week"] = config.day_of_week
    
    if "occupant_counts" not in current_cfg:
        current_cfg["occupant_counts"] = {}
    current_cfg["occupant_counts"]["Office"] = config.occupants
    current_cfg["occupant_counts"]["ConferenceRoom"] = config.occupants * 2
    current_cfg["occupant_counts"]["Lobby"] = max(2, int(config.occupants / 4))
    
    with open(config_path, "w") as f:
        json.dump(current_cfg, f, indent=4)
        
    global control_loop
    if control_loop:
        try:
            if hasattr(control_loop, 'simulator') and control_loop.simulator:
                control_loop.simulator.stop()
        except:
            pass
        control_loop = None
        db_manager.reset_db()
        
    return {"status": "success"}

# Instantiate Database & Control Loop Engine
db_manager = DatabaseManager()
control_loop: Optional[SentinelAIControlLoop] = None
dual_runner: Optional[DualSimulationRunner] = None

# Static directory pathing
_HERE = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD_DIR = os.path.join(os.path.dirname(_HERE), "dashboard")
_STATIC_DIR = os.path.join(_DASHBOARD_DIR, "static")

if os.path.exists(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

@app.get("/favicon.ico", status_code=204)
def favicon():
    return None

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serves the BMS Control Dashboard web UI."""
    index_path = os.path.join(_DASHBOARD_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SentinelAI BMS Control API Active</h1><p>Dashboard HTML loading...</p>"

@app.get("/api/status")
def get_system_status():
    """Returns general system status and active configuration."""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM BuildingState;")
        total_steps = cursor.fetchone()[0]

    return {
        "status": "ONLINE",
        "system": "SentinelAI BMS Autonomous Platform",
        "total_recorded_steps": total_steps,
        "energyplus_available": True,
        "mode": "REAL_TIME_CLOSED_LOOP"
    }

@app.get("/api/state/latest")
def get_latest_state():
    """Returns the most recent BuildingState recorded in SQLite."""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM BuildingState ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            return {"status": "NO_DATA", "message": "No building state recorded yet."}
        
        data = dict(row)
        if data.get("zones_json"):
            data["zones"] = json.loads(data["zones_json"])
        if data.get("telemetry_json"):
            data["telemetry"] = json.loads(data["telemetry_json"])
        return data

@app.get("/api/state/history")
def get_state_history(limit: int = 30):
    """Returns recent building state telemetry for chart rendering."""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM BuildingState ORDER BY id DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
        
        result = []
        for r in reversed(rows):
            d = dict(r)
            if d.get("zones_json"):
                d["zones"] = json.loads(d["zones_json"])
            if d.get("telemetry_json"):
                d["telemetry"] = json.loads(d["telemetry_json"])
            result.append(d)
        return result

@app.get("/api/council/latest")
def get_latest_council_decision():
    """Returns the latest Agent Council decision and 4-perspective reasoning."""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM AgentDecision ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            return {"status": "NO_DATA", "message": "No council decisions recorded yet."}
        
        d = dict(row)
        if d.get("recommended_action_json"):
            d["recommended_action"] = json.loads(d["recommended_action_json"])
        return d

@app.get("/api/validator/logs")
def get_validator_logs(limit: int = 10):
    """Returns recent Safety Validator evaluation logs and self-corrections."""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ValidatorLog ORDER BY id DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            if d.get("violated_rules_json"):
                d["violated_rules"] = json.loads(d["violated_rules_json"])
            if d.get("action_json"):
                d["action"] = json.loads(d["action_json"])
            if d.get("applied_action_json"):
                d["applied_action"] = json.loads(d["applied_action_json"])
            result.append(d)
        return result

@app.get("/api/health/latest")
def get_latest_health():
    """Returns the latest Equipment Health Engine diagnostics and active alerts without mutating state on GET."""
    global control_loop
    if control_loop and control_loop.health_engine and control_loop.health_engine.latest_report:
        report = control_loop.health_engine.latest_report
        return {
            "overall_health_score": report.overall_health_score,
            "status": "NORMAL",
            "assets": {
                k: {
                    "health_score": v.health_score,
                    "status": v.status,
                    "stress_index": v.stress_index,
                    "rul_hours": v.rul_hours
                } for k, v in report.assets.items()
            },
            "active_alerts": [a.__dict__ for a in report.active_alerts]
        }
    
    try:
        health_data = db_manager.get_latest_equipment_health()
    except Exception:
        health_data = None
    if not health_data:
        return {"status": "NO_DATA", "message": "No equipment health report recorded yet."}

    def _asset_payload(health: float, status: Optional[str], power_kw: float, runtime_hours: float, cycling_count: int, nominal_life_hours: float):
        resolved_status = status or ("CRITICAL" if health < 40 else "DEGRADED" if health < 75 else "NORMAL")
        stress_index = round((runtime_hours * 0.001) + (cycling_count * 0.2) + (1.0 if power_kw > 25.0 else 0.0) * 0.5, 2)
        stress_factor = 1.0 + (0.1 * stress_index)
        rul_hours = round(max(0.0, (nominal_life_hours - runtime_hours) * (health / 100.0) / stress_factor), 1)
        return {
            "health_score": round(health, 1),
            "status": resolved_status,
            "stress_index": stress_index,
            "rul_hours": rul_hours,
        }

    p_health = health_data.get("pump_health", 0.0)
    c_health = health_data.get("chiller_health", 0.0)
    a_health = health_data.get("ahu_health", 0.0)
    f_health = health_data.get("fan_health", 0.0)
    power_kw = health_data.get("total_power_kw", 0.0)
    runtime_hours = health_data.get("cumulative_runtime_hours", 0.0)
    cycling_count = health_data.get("cycling_count", 0)
    overall = round((a_health + c_health + p_health + f_health) / 4.0, 1)
    
    return {
        "overall_health_score": overall,
        "status": "CRITICAL" if overall < 40 else "DEGRADED" if overall < 75 else "NORMAL",
        "assets": {
            "AHU": _asset_payload(a_health, health_data.get("ahu_status"), power_kw, runtime_hours, cycling_count, 50000.0),
            "CHILLER": _asset_payload(c_health, health_data.get("chiller_status"), power_kw, runtime_hours, cycling_count, 60000.0),
            "PUMP": _asset_payload(p_health, health_data.get("pump_status"), power_kw, runtime_hours, cycling_count, 35000.0),
            "FAN": _asset_payload(f_health, health_data.get("fan_status"), power_kw, runtime_hours, cycling_count, 40000.0)
        },
        "active_alerts": []
    }

@app.get("/api/comparison/latest")
def get_latest_comparison():
    """Returns the latest empirical Baseline vs SentinelAI comparison metrics."""
    default_result = {
        "energy_saved_pct": 0.0,
        "carbon_reduced_pct": 0.0,
        "comfort_improvement": 0.0,
        "baseline_energy_kwh": 0.0,
        "ai_energy_kwh": 0.0,
        "baseline_pmv": 0.0,
        "ai_pmv": 0.0
    }
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM AISimulationMetrics ORDER BY id DESC LIMIT 1;")
            ai_row = cursor.fetchone()
            
            if not ai_row:
                return default_result
            
            ai_d = dict(ai_row)
            b_d = db_manager.get_latest_baseline_metrics(ai_d["timestep"]) or {}

            baseline_pmv = b_d.get("avg_pmv", ai_d.get("avg_pmv", 0.0))
            ai_pmv = ai_d.get("avg_pmv", 0.0)

            return {
                "timestep": ai_d["timestep"],
                "energy_saved_pct": ai_d.get("energy_saved_pct", 0.0),
                "carbon_reduced_pct": ai_d.get("carbon_reduced_pct", 0.0),
                "comfort_improvement": round(abs(baseline_pmv) - abs(ai_pmv), 3),
                "baseline_energy_kwh": b_d.get("total_energy_kwh", ai_d["total_energy_kwh"]),
                "ai_energy_kwh": ai_d["total_energy_kwh"],
                "baseline_pmv": baseline_pmv,
                "ai_pmv": ai_pmv
            }
    except Exception as e:
        logger.warning(f"Comparison query failed: {e}")
        return default_result

baseline_runner = None
@app.post("/api/control/step")
def trigger_step():
    """Triggers 1 autonomous closed-loop simulation step."""
    global control_loop, baseline_runner
    if not baseline_runner:
        from backend.building.baseline_runner import BaselineSimulationRunner
        baseline_runner = BaselineSimulationRunner(db_manager=db_manager, use_energyplus=True)
    if not control_loop:
        control_loop = SentinelAIControlLoop(db_path=db_manager.db_path, use_energyplus=True)
    
    baseline_runner.run_step()
    result = control_loop.run_step()
    return {
        "status": "SUCCESS",
        "timestep": result["timestep"],
        "validated": result["validation_result"].is_valid,
        "fallback_used": result["validation_result"].used_fallback
    }

@app.post("/api/control/dual_step")
def trigger_dual_step():
    """Triggers 1 side-by-side Dual Simulation comparison step."""
    global dual_runner
    if not dual_runner:
        dual_runner = DualSimulationRunner(db_path=db_manager.db_path, use_energyplus=True)
    res = dual_runner.run_dual_simulation(num_steps=1)
    return {
        "status": "SUCCESS",
        "comparison": res[0] if res else {}
    }

@app.post("/api/health/regen")
def trigger_equipment_regen(asset: str = "PUMP"):
    """Triggers maintenance rotation or servicing for any degraded HVAC asset (AHU, CHILLER, PUMP, FAN)."""
    global control_loop
    eq_key = asset.upper()
    try:
        target_eq = EquipmentType[eq_key]
    except KeyError:
        target_eq = EquipmentType.PUMP

    if control_loop and control_loop.health_engine:
        control_loop.health_engine.apply_regeneration_switch(target_eq, boost_pct=25.0)
        state = control_loop.state_manager.current_state
        if state:
            report = control_loop.health_engine.evaluate_state(state)
            db_manager.log_equipment_health_report(report)
        return {"status": "SUCCESS", "asset": target_eq.value, "new_health": control_loop.health_engine.health_scores.get(target_eq, 95.0)}
    return {"status": "SUCCESS", "asset": target_eq.value}

@app.post("/api/database/reset")
def reset_database():
    """Purges all SQLite simulation tables and resets the control loop state back to timestep 0."""
    global control_loop, dual_runner, baseline_runner
    
    # 1. STOP THREADS FIRST to prevent them from writing to DB after we clear it!
    if control_loop and hasattr(control_loop, "simulator"):
        control_loop.simulator.stop()
    if baseline_runner and hasattr(baseline_runner, "runner"):
        baseline_runner.runner.stop()
    if dual_runner:
        if hasattr(dual_runner, "ai_loop") and hasattr(dual_runner.ai_loop, "simulator"):
            dual_runner.ai_loop.simulator.stop()
        if hasattr(dual_runner, "baseline_runner") and hasattr(dual_runner.baseline_runner, "runner"):
            dual_runner.baseline_runner.runner.stop()
            
    control_loop = None
    dual_runner = None
    baseline_runner = None

    db_manager.reset_db()

    return {"status": "SUCCESS", "message": "Database file permanently deleted and recreated cleanly"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, reload=True)
