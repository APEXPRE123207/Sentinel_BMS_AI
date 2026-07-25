# 🏢 SentinelAI: Health-Aware Autonomous Building Intelligence Platform

**SentinelAI** is an autonomous Building Management System (BMS) built around **EnergyPlus**, an **Open-Source LLM**, and the **Model Context Protocol (MCP)**. It continuously monitors building operation, reasons across multiple conflicting objectives (energy, comfort, carbon, equipment health), validates actions against safety constraints, and updates operating parameters in a closed loop.

---

## 🚀 Environment Setup (Conda)

### 1. Create and Activate Conda Environment
```bash
conda create -n sentinelai python=3.10 -y
conda activate sentinelai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🧪 Running Tests & Autonomous Closed Loop

### Run Automated Unit & Integration Tests
```bash
python -m pytest tests/test_closed_loop.py -v
```

### Run 10-Step Autonomous Control Loop
```bash
python -m backend.run_loop
```

---

## ⚡ EnergyPlus Integration Setup

When your EnergyPlus installation finishes:
1. Ensure EnergyPlus is installed (e.g. `C:\EnergyPlusV23-2-0` or default installer directory).
2. Add EnergyPlus Python API path to your environment or `PYTHONPATH`:
   ```bash
   set PYTHONPATH=C:\EnergyPlusV23-2-0;%PYTHONPATH%
   ```
3. The `EnergyPlusAPIAdapter` in `backend/energyplus/runner.py` will automatically detect and bind to `pyenergyplus.api`.

---

## 📂 Project Architecture

```
SentinelAI/
├── backend/
│   ├── database/
│   │   ├── db.py                 # SQLite database manager & tables
│   │   └── models.py             # Data models for State, Action, Validator & Telemetry
│   ├── state/
│   │   ├── state_manager.py      # Single source of truth for building state
│   │   └── context_builder.py    # 10-step rolling window context summarizer
│   ├── mcp/
│   │   └── tools.py              # MCP sensor & actuator tool definitions
│   ├── agents/
│   │   └── council.py            # Structured Agent Council (Energy, Comfort, Carbon, Health)
│   ├── validator/
│   │   └── safety_validator.py   # Safety Validator + Retry loop + Last Known Good (LKG) fallback
│   ├── controller/
│   │   └── forward_controller.py # Actuator forward controller
│   ├── energyplus/
│   │   └── runner.py             # Multi-zone building physics simulation & EnergyPlus API adapter
│   └── run_loop.py               # Autonomous closed-loop runner
├── tests/
│   └── test_closed_loop.py       # Integration tests
├── requirements.txt
└── README.md
```
