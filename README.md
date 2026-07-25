# 🏢 SentinelAI: Health-Aware Autonomous Building Intelligence Platform

> **Honeywell Building Automation Hackathon Project**  
> An autonomous Building Management System (BMS) integrating **EnergyPlus**, an **Open-Source LLM**, and the **Model Context Protocol (MCP)** to operate a closed-loop control system optimizing across **Energy**, **Comfort**, **Carbon**, and **Equipment Health**.

---

## 🌟 Key Architectural Innovations (v2.0)

SentinelAI transforms conventional static-schedule Building Management Systems into a self-healing, multi-objective autonomous cyber-physical platform:

- ⚡ **Single-Call Structured Agent Council**: Evaluates 4 competing objectives simultaneously (Energy, Comfort, Carbon, Equipment Health) in a single LLM prompt, returning structured JSON recommendations.
- 🛡️ **Modular Safety Validator & Self-Correction**: Enforces 9 hard physical, rate-limit, comfort, and equipment rules across 4 categories (`PHYSICAL`, `RATE_LIMIT`, `COMFORT`, `EQUIPMENT`). Provides structured feedback for LLM retries and falls back to **Last-Known-Good (LKG)** state if validation fails.
- 📊 **State Manager (Single Source of Truth)**: Centralized state manager that reads simulation variables, weather, occupancy, and equipment telemetry, logging atomically to SQLite.
- 📈 **Rolling Context Builder**: Summarizes a 10-step rolling window of building trends for lightweight, high-performance LLM prompting.
- 🔬 **Baseline Comparison Framework**: Dual simulation runner (`baseline.idf` vs `sentinel.idf`) providing real empirical measurement of Energy Saved (%), Carbon Reduced (%), Comfort Improvement, and Stress Reduction.
- 🔌 **Real EnergyPlus Integration**: Connects directly to `pyenergyplus.api` (EnergyPlus C-API & Python API) with zero data synthesis.

---

## 📅 Project Phase Status

| Phase | Description | Status |
| :--- | :--- | :---: |
| **Phase 1** | **Core Control Loop & Real EnergyPlus Integration** | ✅ **Completed** |
| **Phase 2** | **Modular 9-Rule Safety Engine & LKG Serialization** | ✅ **Completed** |
| **Phase 3** | **Baseline Comparison Framework & Dual Simulation** | ✅ **Completed** |
| **Phase 4** | **Equipment Health Engine (Stress, RUL, Anomaly)** | 📋 Planned |
| **Phase 5** | **Live Analytics & Decision Dashboard (FastAPI + Plotly)** | 📋 Planned |
| **Phase 6** | **Interactive 2D/3D Digital Twin Visualizer** | 📋 Planned |
| **Phase 7** | **Demo Scenario, Video & Presentation** | 📋 Planned |

---

## 🛠️ Environment Setup & Quickstart

### 1. Prerequisites
- **Python 3.10** (Recommended via Conda)
- **EnergyPlus** (Installed at `D:\EnergyPlus` or `C:\EnergyPlusV23-2-0`)

### 2. Conda Environment Setup
```bash
# Create and activate Conda environment
conda create -n sentinelai python=3.10 -y
conda activate sentinelai

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running SentinelAI

### 1. Run Autonomous Closed-Loop Control (Real EnergyPlus)
```bash
python -m backend.run_loop --steps 10 --energyplus
```

### 2. Run Side-by-Side Dual Simulation (Baseline vs SentinelAI)
```bash
python -m backend.building.dual_runner --steps 10
```

### 3. Run Test Suite (41 Automated Tests)
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📁 Repository Structure

```
Sentinel_BMS_AI/
├── backend/
│   ├── database/
│   │   ├── db.py                 # SQLite database manager & 6 log tables
│   │   └── models.py             # Dataclasses & Pydantic schemas
│   ├── state/
│   │   ├── state_manager.py      # Single source of truth for telemetry & state
│   │   └── context_builder.py    # 10-step rolling window context builder
│   ├── mcp/
│   │   └── tools.py              # MCP sensor & actuator tool definitions
│   ├── agents/
│   │   └── council.py            # Single-call Agent Council (Energy, Comfort, Carbon, Health)
│   ├── validator/
│   │   ├── rules.py              # 9 modular safety rules across 4 categories
│   │   └── safety_validator.py   # Safety Validator + Feedback Generator + LKG Serialization
│   ├── controller/
│   │   └── forward_controller.py # Actuator command translator
│   ├── analytics/
│   │   └── comparator.py         # Empirical baseline vs AI comparison math
│   ├── energyplus/
│   │   └── runner.py             # Real pyenergyplus.api background runner & physics engine
│   ├── building/
│   │   ├── baseline.idf          # Baseline building model (static schedule)
│   │   ├── sentinel.idf          # SentinelAI building model (dynamic actuation)
│   │   ├── baseline_runner.py    # Baseline EnergyPlus runner
│   │   └── dual_runner.py        # Side-by-side Dual Simulation runner
│   └── run_loop.py               # Autonomous closed-loop orchestrator
├── tests/
│   ├── test_closed_loop.py       # Integration tests
│   ├── test_safety_rules.py      # 33 safety rule tests
│   └── test_baseline_comparison.py # Baseline comparison tests
├── PHASES.md                     # Master project roadmap & context reference
├── Project_plan.md               # Original project blueprint & v2.0 specs
├── requirements.txt              # Project dependencies
└── README.md                     # Documentation
```

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
