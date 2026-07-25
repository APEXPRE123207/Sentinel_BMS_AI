# 🚀 SentinelAI: Master Phase Roadmap & Context Reference

> **Project Vision**: SentinelAI is an autonomous, self-healing Building Management System (BMS) integrating **EnergyPlus**, an **Open-Source LLM**, and the **Model Context Protocol (MCP)** to operate a closed-loop control system optimizing across Energy, Comfort, Carbon, and Equipment Health.

---

## 📌 Architecture & Design Baseline (v1.0 + v2.0 Updates)

- **Agent Council (v2.0)**: Single structured LLM prompt generating JSON reasoning across 4 perspectives (Energy, Comfort, Carbon, Health) + action recommendation.
- **Safety Validator (v2.0)**: Self-correcting loop with 1-attempt retry with feedback, falling back to Last-Known-Good (LKG) control parameters if rejected.
- **State Manager (v2.0)**: Central single source of truth reading simulation variables, weather, occupancy, and telemetry, logging atomically to SQLite.
- **Rolling Context Builder (v2.0)**: Maintains a 10-step rolling context window summarizing trends for light-weight LLM prompts.
- **Baseline Framework**: Dual simulation runner (`baseline.idf` vs `sentinel.idf`) measuring empirical savings.
- **Equipment Health Engine**: Computes Health Score (%), Stress Index, and Remaining Useful Life (RUL).

---

## 📅 Complete 7-Phase Execution Plan

```
Phase 1: Core Control Loop & Backend Foundation [COMPLETED]
   │
   ▼
Phase 2: Enhanced Safety Validator & Self-Correction [COMPLETED]
   │
   ▼
Phase 3: Baseline Comparison Framework & Dual Simulation [COMPLETED]
   │
   ▼
Phase 4: Equipment Health Engine [COMPLETED]
   │
   ▼
Phase 5: Live Dashboard & Analytics UI [COMPLETED]
   │
   ▼
Phase 6: Interactive Digital Twin, Cloud LLM & Critical Fixes [COMPLETED]
   │
   ▼
Phase 7: Presentation, Demo Scenario & Polish [PLANNED]
```

---

### Phase 1: Core Control Loop & Backend Foundation
**Status**: ✅ **COMPLETED** (Real EnergyPlus `pyenergyplus.api` C-API & Python API integration verified on `D:\EnergyPlus`)

#### Key Deliverables & Files Built:
- **Database & Data Models**:
  - [`backend/database/models.py`](file:///w:/CODE/Honeywell/backend/database/models.py): Data models for `BuildingState`, `ZoneState`, `EquipmentTelemetry`, `ActionRecommendation`, `AgentCouncilDecision`, `ValidationResult`.
  - [`backend/database/db.py`](file:///w:/CODE/Honeywell/backend/database/db.py): SQLite database manager creating 6 tables (`BuildingState`, `AgentDecision`, `ValidatorLog`, `EquipmentHealth`, `BaselineMetrics`, `AISimulationMetrics`).
- **State Engine**:
  - [`backend/state/state_manager.py`](file:///w:/CODE/Honeywell/backend/state/state_manager.py): Single source of truth & SQLite state logger.
  - [`backend/state/context_builder.py`](file:///w:/CODE/Honeywell/backend/state/context_builder.py): 10-step rolling window context builder.
- **MCP Tool Server**:
  - [`backend/mcp/tools.py`](file:///w:/CODE/Honeywell/backend/mcp/tools.py): Sensor and actuator MCP tools (`get_zone_temperature`, `set_hvac_setpoint`, `set_airflow`, etc.).
- **Structured Agent Council**:
  - [`backend/agents/council.py`](file:///w:/CODE/Honeywell/backend/agents/council.py): Structured single-call Agent Council with LLM API driver + deterministic fallback council.
- **Safety Validator & Controller**:
  - [`backend/validator/safety_validator.py`](file:///w:/CODE/Honeywell/backend/validator/safety_validator.py): Physical bounds validator with retry feedback and LKG fallback.
  - [`backend/controller/forward_controller.py`](file:///w:/CODE/Honeywell/backend/controller/forward_controller.py): Actuator mapper.
- **Simulation & Real EnergyPlus Control Loop**:
  - [`backend/energyplus/runner.py`](file:///w:/CODE/Honeywell/backend/energyplus/runner.py): Real `EnergyPlusRunner` using `pyenergyplus.api` background thread with zone-timestep callbacks, sensor variable reads, and actuator writes (`small_office.idf` + `weather.epw`). Built-in `SimulationEngine` retained as fallback.
  - [`backend/run_loop.py`](file:///w:/CODE/Honeywell/backend/run_loop.py): Closed loop orchestrator (`Observe -> State Manager -> Context -> Council -> Validator -> Controller -> Execute -> Log`). Supports `--energyplus` CLI flag.
- **Tests & Environment**:
  - [`tests/test_closed_loop.py`](file:///w:/CODE/Honeywell/tests/test_closed_loop.py): Integration test suite.
  - [`requirements.txt`](file:///w:/CODE/Honeywell/requirements.txt): Dependencies for Conda.
  - [`README.md`](file:///w:/CODE/Honeywell/README.md): Setup & execution guide.

---

### Phase 2: Enhanced Safety Validator & Self-Correction
**Status**: ✅ **COMPLETED**

#### Objectives:
- Expand safety validator rules to cover PMV thermal comfort bounds (PMV between $-0.5$ and $+0.5$).
- Add equipment limit protections (chiller minimum run time, fan maximum static pressure).
- Refine feedback prompt generation for LLM retries when an action is rejected.
- Implement state serialization for Last-Known-Good (LKG) parameters.

#### Key Deliverables & Files Built:
- **Modular Rules Engine**:
  - [`backend/validator/rules.py`](file:///w:/CODE/Honeywell/backend/validator/rules.py): 9 modular safety rules across 4 categories (PHYSICAL, RATE_LIMIT, COMFORT, EQUIPMENT).
- **Enhanced Safety Validator**:
  - [`backend/validator/safety_validator.py`](file:///w:/CODE/Honeywell/backend/validator/safety_validator.py): Refactored to use modular rules, structured LLM feedback generation (`build_feedback_prompt`), and LKG JSON serialization/deserialization.
- **Data Models**:
  - [`backend/database/models.py`](file:///w:/CODE/Honeywell/backend/database/models.py): Added `RuleViolation` dataclass and `rule_violations` field to `ValidationResult`.
- **Run Loop Integration**:
  - [`backend/run_loop.py`](file:///w:/CODE/Honeywell/backend/run_loop.py): Passes `building_state` to validator for live PMV/CO₂/equipment checks; uses structured feedback prompts for LLM retries.
- **Test Suite**:
  - [`tests/test_safety_rules.py`](file:///w:/CODE/Honeywell/tests/test_safety_rules.py): 33 dedicated tests covering all 9 rules, integrated validator, structured feedback, and LKG serialization.

---

### Phase 3: Baseline Comparison Framework & Dual Simulation
**Status**: ✅ **COMPLETED**

#### Objectives & User Constraints Met:
- **Zero Synthesized Data**: 100% of baseline and AI metrics pulled directly from real EnergyPlus runtime output variables (`pyenergyplus.api`).
- Dual EnergyPlus models (`baseline.idf` vs `sentinel.idf`) configured with explicit `Output:Variable` definitions (`Facility Total Electricity Demand Rate`, `Zone Mean Air Temperature`, `Zone Air Relative Humidity`, `Zone Air CO2 Concentration`).

#### Key Deliverables & Files Built:
- **Dual Building Models**:
  - [`backend/building/baseline.idf`](file:///w:/CODE/Honeywell/backend/building/baseline.idf): Un-controlled baseline model operating on default static schedules.
  - [`backend/building/sentinel.idf`](file:///w:/CODE/Honeywell/backend/building/sentinel.idf): SentinelAI-controlled model with dynamic EMS/Python API actuation.
- **Baseline Simulation Runner**:
  - [`backend/building/baseline_runner.py`](file:///w:/CODE/Honeywell/backend/building/baseline_runner.py): Executes un-controlled Baseline EnergyPlus simulation and logs raw metrics directly to SQLite `BaselineMetrics`.
- **Comparative Analytics Engine**:
  - [`backend/analytics/comparator.py`](file:///w:/CODE/Honeywell/backend/analytics/comparator.py): Calculates real empirical performance improvements (Energy Saved %, Carbon Reduced %, Comfort Improvement, Equipment Stress Reduction) and logs to SQLite `AISimulationMetrics`.
- **Dual Simulation Runner**:
  - [`backend/building/dual_runner.py`](file:///w:/CODE/Honeywell/backend/building/dual_runner.py): Orchestrates side-by-side execution of Baseline and SentinelAI EnergyPlus simulations on the exact same weather EPW file.
- **Test Suite**:
  - [`tests/test_baseline_comparison.py`](file:///w:/CODE/Honeywell/tests/test_baseline_comparison.py): Unit and integration tests verifying baseline metrics logging, comparison math, and dual simulation execution.

---

### Phase 4: Equipment Health Engine
**Status**: ✅ **COMPLETED**

#### Key Deliverables & Files Built:
- **Health Engine Models**:
  - [`backend/health_engine/models.py`](file:///w:/CODE/Honeywell/backend/health_engine/models.py): Data models for `AssetHealthReport`, `OverallBuildingHealthReport`, `EquipmentStressDetails`, `AnomalyDetectionResult`, and `PredictiveMaintenanceAlert`.
- **Standalone Health Engine**:
  - [`backend/health_engine/engine.py`](file:///w:/CODE/Honeywell/backend/health_engine/engine.py): Asset degradation math, Stress Index (0-10+), RUL estimation in operating hours, Anomaly Detection (power surges, rapid cycling, degradation), and Predictive Maintenance Alerts for AHU, Pump, Fan, and Chiller.
- **Database & Agent Council Integration**:
  - [`backend/database/db.py`](file:///w:/CODE/Honeywell/backend/database/db.py): Extended DatabaseManager with `log_equipment_health_report()` logging directly to `EquipmentHealth` SQLite table.
  - [`backend/run_loop.py`](file:///w:/CODE/Honeywell/backend/run_loop.py): Automated health evaluation step in control loop.
- **Test Suite**:
  - [`tests/test_health_engine.py`](file:///w:/CODE/Honeywell/tests/test_health_engine.py): Unit and integration test suite covering degradation math, RUL estimation, stress index, anomaly detection, alert generation, and SQLite persistence.

---

### Phase 5: Live Dashboard & Analytics UI
**Status**: ✅ **COMPLETED**

#### Key Deliverables & Files Built:
- **FastAPI REST API Service**:
  - [`backend/api/main.py`](file:///w:/CODE/Honeywell/backend/api/main.py): REST endpoints for live building state, Agent Council 4-perspective reasoning, Safety Validator logs, Equipment Health diagnostics, and Baseline vs SentinelAI empirical comparison metrics. Supports interactive step execution endpoints (`/api/control/step`, `/api/control/dual_step`).
- **BMS Web Control Dashboard**:
  - [`backend/dashboard/index.html`](file:///w:/CODE/Honeywell/backend/dashboard/index.html): Dark mode control center UI featuring live status LEDs, outdoor Chicago weather widget, vital metric cards, AI council reasoning panel, safety validator feed, equipment diagnostics table, and live Plotly.js charts.
  - [`backend/dashboard/static/styles.css`](file:///w:/CODE/Honeywell/backend/dashboard/static/styles.css): Premium dark industrial design system tokens, glassmorphism cards, and responsive flex/grid layouts.
  - [`backend/dashboard/static/app.js`](file:///w:/CODE/Honeywell/backend/dashboard/static/app.js): Asynchronous REST API polling, dynamic UI updates, interactive control triggers, and live Plotly.js chart rendering.
- **Test Suite**:
  - [`tests/test_dashboard_api.py`](file:///w:/CODE/Honeywell/tests/test_dashboard_api.py): Integration test suite verifying all `/api/*` REST endpoints and dashboard HTML rendering.

---

### Phase 6: Interactive Digital Twin, Cloud LLM & Critical Fixes
**Status**: ✅ **COMPLETED**

#### Key Deliverables & Files Built:
- **Interactive Digital Twin (Hybrid SVG + Three.js)**:
  - [`backend/dashboard/static/digital_twin.js`](file:///w:/CODE/Honeywell/backend/dashboard/static/digital_twin.js): Dual-renderer digital twin visualization — SVG safety-net renderer + Three.js orthographic scene with `MeshBasicMaterial` (no lighting), `OrthographicCamera` (fixed isometric, no orbit), `BoxGeometry` rooms only. Equipment health dots are HTML overlays projected from 3D coordinates. Raycaster-based click interaction for room selection.
- **Cloud LLM Integration**:
  - [`backend/agents/council.py`](file:///w:/CODE/Honeywell/backend/agents/council.py): Multi-provider LLM routing — Ollama Cloud API (`OLLAMA_API_KEY` → `ollama.com/api/chat`), Google Gemini API (`LLM_API_KEY`), or local Ollama fallback (`LLM_API_KEY=0`). Includes deterministic fallback council for offline execution.
- **EnergyPlus Fixes**:
  - All 3 IDF files (`small_office.idf`, `baseline.idf`, `sentinel.idf`): Added `Zone People Occupant Count`, `Site Outdoor Air Drybulb Temperature`, `Site Outdoor Air Relative Humidity` output variables. Updated occupancy counts (Office=8, Conference=15, Lobby=2). Swapped RunPeriod to July 7 (summer) for meaningful cooling loads.
  - [`backend/energyplus/runner.py`](file:///w:/CODE/Honeywell/backend/energyplus/runner.py): Fixed thread synchronization race condition in `step()`. Switched weather reading from unreliable `today_weather_*` API to standard output variables.
- **API & Infrastructure Fixes**:
  - [`backend/api/main.py`](file:///w:/CODE/Honeywell/backend/api/main.py): Fixed Reset DB (`initialize_tables` → `_init_db`). Added crash protection (`try/except`) to `/api/comparison/latest` and `/api/health/latest` endpoints.
  - [`backend/analytics/comparator.py`](file:///w:/CODE/Honeywell/backend/analytics/comparator.py): Fixed operator precedence bug in `ai_stress` calculation.
  - [`.gitignore`](file:///w:/CODE/Honeywell/.gitignore): Added `.env` and `api_key` to prevent secret leakage.

---

### Phase 7: Presentation, Demo Scenario & Final Polish
**Status**: 📋 **PLANNED**

#### Objectives:
- Script and validate end-to-end hackathon demo scenario:
  - **Scenario**: Conference room occupancy spike → temperature rises → pump health degrades → Agent Council negotiates → Supervisor selects action → Safety Validator approves → EnergyPlus updates → Dashboard & Digital Twin update live.
- Record demo video and prepare project documentation (`docs/architecture.md`, `README.md`, slide deck).

---

## 🗄️ Database Schema Summary

| Table | Purpose |
| :--- | :--- |
| `BuildingState` | Stores every simulation timestep (outdoor temp, humidity, zones JSON, telemetry JSON). |
| `AgentDecision` | Stores every AI recommendation (energy, comfort, carbon, health reasoning & recommended actions). |
| `ValidatorLog` | Stores validation results (valid/invalid, attempt number, violated rules, LKG fallback flag). |
| `EquipmentHealth` | Stores equipment health scores (AHU, Pump, Fan, Chiller, runtime, cycling count). |
| `BaselineMetrics` | Stores baseline un-controlled simulation metrics. |
| `AISimulationMetrics` | Stores AI-controlled simulation metrics & calculated % savings. |

---

## ⚡ Quick Reference Commands

```bash
# Activate Conda Environment
conda activate sentinelai

# Install Dependencies
pip install -r requirements.txt

# Run Automated Test Suite
python -m pytest tests/test_closed_loop.py -v

# Run 10-Step Autonomous Control Loop
python -m backend.run_loop

# Launch Dashboard & API Server (Phase 5+6)
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```
