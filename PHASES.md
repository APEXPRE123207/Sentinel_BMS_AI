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
Phase 4: Equipment Health Engine [PLANNED]
   │
   ▼
Phase 5: Live Dashboard & Analytics UI [PLANNED]
   │
   ▼
Phase 6: Interactive Digital Twin [PLANNED]
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
**Status**: 📋 **PLANNED**

#### Objectives:
- Build standalone Health Engine computing:
  - Health Score (0-100%) for AHU, Pump, Fan, and Chiller.
  - Stress Index based on runtime hours, excessive cycling, thermal overload, and abnormal power draw.
  - Remaining Useful Life (RUL) estimation.
  - Anomaly Detection score.
- Expose health recommendations directly to the Agent Council Health perspective.

#### Target Files:
- `backend/health_engine/engine.py`
- `backend/health_engine/models.py`

---

### Phase 5: Live Dashboard & Analytics UI
**Status**: 📋 **PLANNED**

#### Objectives:
- Build FastAPI backend API endpoints serving real-time building state, AI decisions, validator logs, and baseline comparisons.
- Develop interactive web dashboard (React or Streamlit):
  - **Building Vital Metrics Cards** (Energy, Carbon, Comfort, Health).
  - **AI Reasoning Panel** (Displaying Council Energy/Comfort/Carbon/Health thoughts & confidence).
  - **Live Charts** (Plotly charts for Temperature, Power, Occupancy, Carbon).
  - **Scenario Comparison** (Baseline vs AI).

#### Target Files:
- `backend/dashboard/api.py` (FastAPI backend)
- `frontend/` (React or Streamlit dashboard application)

---

### Phase 6: Interactive Digital Twin
**Status**: 📋 **PLANNED**

#### Objectives:
- Build interactive building visualization (SVG / 2D / Three.js):
  - **Room Heatmap View**: Click room (Office, Conference Room, Lobby) to view live temp, humidity, occupancy, PMV, and current AI decision.
  - **Equipment Health Overlay**: Visual status indicators for AHU (🟢), Pump (🟡), Fan (🔴), Chiller (🟢).
  - **Timeline Playback**: Step-by-step playback of building events (e.g. 09:10 Occupancy ↑ → Temp ↑ → Pump degradation → AI action → Comfort restored).

#### Target Files:
- `frontend/src/components/DigitalTwin.jsx` or Streamlit custom visualizer.

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
```
