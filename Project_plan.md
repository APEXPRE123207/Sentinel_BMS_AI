SentinelAI: Health-Aware Autonomous Building Intelligence Platform
Project Vision
SentinelAI is an autonomous Building Management System (BMS) built around EnergyPlus, an open-source LLM, and the Model Context Protocol (MCP). It continuously observes a simulated building, reasons over multiple objectives (energy, comfort, carbon, equipment health), validates actions, and updates operating parameters in a closed loop.

Objectives
• Reduce energy consumption while maintaining thermal comfort.
• Reduce carbon emissions.
• Increase equipment lifetime through health-aware scheduling.
• Demonstrate fully autonomous closed-loop building control.
• Provide explainable AI decisions through an interactive dashboard.
Tech Stack
Simulation: EnergyPlus + Python API
AI: Qwen 3 or Llama 3.1 (Open Source)
MCP: Python MCP Server
Backend: Python + FastAPI
Frontend: React (or Streamlit for hackathon)
Charts: Plotly
Database: SQLite
Visualization: SVG/Three.js based Digital Twin (2D first, optional 3D)
Version Control: GitHub
High-Level Architecture
Weather + Occupancy -> EnergyPlus -> Python API -> MCP Server -> Agent Council (Energy, Comfort, Carbon, Health Agents) -> Supervisor Agent -> Safety Validator -> Execution Layer -> EnergyPlus -> Dashboard/Digital Twin.
Core Modules
1. EnergyPlus Interface
2. MCP Tool Server
3. Agent Council
4. Supervisor Agent
5. Safety Validator
6. Forward Controller
7. Equipment Health Engine
8. Digital Twin
9. Dashboard
10. Data Logger & Analytics
Agent Council
Energy Agent: minimizes energy.
Comfort Agent: maintains PMV, temperature, humidity, CO₂.
Carbon Agent: minimizes emissions.
Health Agent: protects pumps, chillers, AHUs, fans.
Supervisor Agent merges recommendations into a single action.
Equipment Health Engine
Computes health score, stress index, remaining useful life, anomaly score and maintenance recommendation from runtime, cycling, power draw and efficiency.
Digital Twin
Interactive building visualization.
Room heatmap.
Equipment health overlay.
Timeline playback.
Current AI decision per room.
Occupancy overlay.
Energy flow overlay.
Dashboard Features
Building Vital Metrics
Energy Savings
Carbon Savings
Comfort Score
Equipment Health
Current AI Reasoning
Historical Trends
Alerts
Scenario Comparison (Baseline vs AI)
MCP Tools
get_zone_temperature()
get_energy_usage()
get_weather()
get_occupancy()
get_equipment_health()
set_hvac_setpoint()
set_airflow()
switch_pump()
set_lighting()
set_ventilation()
Closed Loop
Observe -> Estimate State -> Agent Council -> Supervisor -> Safety Validator -> Execute -> Verify -> Repeat
Folder Structure
backend/
 energyplus/
 mcp/
 agents/
 health_engine/
 validator/
 controller/
 dashboard/
 frontend/
 docs/
 building/
 database/
 tests/
Hackathon Deliverables
1. Source Code
2. EnergyPlus Building Model
3. Interactive Dashboard
4. Architecture Documentation
5. Demo Video
6. GitHub Repository
7. README
Demo Scenario
Occupancy spike in conference room -> temperature rises -> pump health degrades -> agents negotiate -> supervisor selects action -> validator approves -> EnergyPlus updates -> dashboard and digital twin refresh -> energy reduced while comfort maintained.
Future Enhancements
Knowledge Graph
Predictive occupancy
Grid-aware optimization
Demand response
Reinforcement Learning
Self-learning control policies
Fault-tolerant multi-building deployment
Evaluation Mapping
System Integration: EnergyPlus + Python API + MCP + Agent Council + Dashboard.
Energy Savings: Dynamic HVAC optimization.
Thermal Comfort: PMV, humidity, CO₂ and occupancy aware control.
Agentic Autonomy: Multi-agent reasoning with supervisor and validator.
Presentation: Digital Twin, explainable AI, timeline, analytics.
Note
This document is a high-level blueprint intended to guide implementation. A complete industrial design specification would expand each module into detailed APIs, UML diagrams, database schema, algorithms, and implementation details.

SentinelAI
A Self-Healing Autonomous Building Intelligence Platform
________________________________________
1. Problem Statement
Commercial buildings consume approximately 40% of global energy and contribute significantly to carbon emissions. Existing Building Management Systems (BMS) operate on predefined schedules and static rules that cannot adapt to changing weather conditions, occupancy patterns, equipment degradation, or electricity demand.
Current systems may optimize energy consumption, but they rarely reason about multiple conflicting objectives simultaneously. They also lack explainability, predictive decision-making, and autonomous adaptation.
SentinelAI transforms a conventional building into an autonomous cyber-physical system capable of continuously observing, reasoning, validating, and optimizing its operation.
________________________________________
2. Objective
Develop an AI-powered autonomous Building Management System using EnergyPlus as the building simulator and an open-source Large Language Model connected through the Model Context Protocol (MCP).
The system continuously:
•	monitors the building, 
•	reasons over energy, comfort, carbon, and equipment health, 
•	autonomously updates operating parameters, 
•	explains every decision, 
•	continuously improves building performance. 
________________________________________
3. Key Innovation
Most projects optimize only:
Energy ↓
Our project optimizes
Energy

Comfort

Carbon

Equipment Health

Indoor Air Quality

Occupancy

↓

Autonomous Building Intelligence
Instead of treating the building as a collection of sensors,
SentinelAI treats the building as a living intelligent system.
________________________________________
4. Overall Architecture
                        Weather API
                             │
                             │
                     Occupancy Schedule
                             │
                             ▼
                     EnergyPlus Simulation
                             │
                  Python Runtime API
                             │
                Real-Time Sensor Stream
                             │
                    MCP Tool Server
                             │
                   Open Source LLM
                             │
        ┌────────────────────────────────────┐
        │        Agent Council               │
        │                                    │
        │  Energy Agent                      │
        │  Comfort Agent                     │
        │  Carbon Agent                      │
        │  Health Agent                      │
        └────────────────────────────────────┘
                             │
                    Supervisor Agent
                             │
                   Safety Validator
                             │
               Forward Control Actions
                             │
                     EnergyPlus
                             │
                Dashboard + Digital Twin
________________________________________
5. Technology Stack
Simulation
EnergyPlus
Purpose
Digital Twin of the Building
Outputs
•	Room temperatures 
•	HVAC power 
•	Cooling loads 
•	Heating loads 
•	Occupancy 
•	CO₂ 
•	PMV 
•	Humidity 
•	Electricity usage 
________________________________________
Programming Language
Python
Used for
•	EnergyPlus API 
•	MCP Server 
•	Agent orchestration 
•	Health Engine 
•	Dashboard backend 
________________________________________
Open Source LLM
Recommended
Qwen 3
or
Llama 3.1
Reason
Excellent reasoning
Good tool calling
Runs locally
________________________________________
MCP
Python MCP Server
Provides tools
get_zone_temperature()

get_energy_usage()

get_weather()

get_equipment_status()

set_hvac_setpoint()

set_airflow()

change_lighting()

set_ventilation()
________________________________________
Dashboard
React
or
Streamlit
If time becomes tight
Streamlit.
________________________________________
Charts
Plotly
________________________________________
Database
SQLite
Stores
•	historical data 
•	AI decisions 
•	health history 
________________________________________
6. Project Modules
________________________________________
Module 1
EnergyPlus Interface
Purpose
Connect Python with EnergyPlus.
Responsibilities
•	Run simulation 
•	Read live variables 
•	Update actuators 
•	Maintain simulation loop 
Outputs
Temperature

Humidity

PMV

Power

CO₂

Lighting

HVAC

Occupancy
________________________________________
Module 2
MCP Server
Purpose
Provide structured tools for the LLM.
Instead of
reading CSV files,
the LLM calls tools.
Example
get_temperature()

set_hvac()

get_room_status()

get_energy()
________________________________________
Module 3
Agent Council
This is our biggest architectural innovation.
Instead of one LLM,
we create multiple specialists.
________________________________________
Energy Agent
Goal
Minimize electricity.
Looks at
•	HVAC load 
•	lighting 
•	occupancy 
Outputs
Energy recommendation.
________________________________________
Comfort Agent
Goal
Maintain
PMV
Temperature
Humidity
CO₂
Outputs
Comfort recommendation.
________________________________________
Carbon Agent
Goal
Reduce emissions.
Uses
Grid emission factor
Electricity usage
Weather
Outputs
Carbon recommendation.
________________________________________
Health Agent
Our novelty.
Computes
Pump Health

Fan Health

AHU Health

Chiller Health
based on
runtime
power
efficiency
temperature
cycling
Outputs
Health recommendation.
________________________________________
Module 4
Supervisor Agent
Receives
four recommendations.
Example
Energy

↓

Increase setpoint

Comfort

↓

Decrease setpoint

Health

↓

Switch Pump

Carbon

↓

Delay Cooling
Supervisor balances all objectives.
Returns
one decision.
________________________________________
Module 5
Safety Validator
This module protects the building.
Before
EnergyPlus receives any command
Validator checks
Comfort
Temperature
Humidity
Safety
Equipment limits
Example
LLM
Turn HVAC OFF
Validator
Reject
Comfort violation.
Only valid actions proceed.
________________________________________
Module 6
Forward Controller
Converts
AI decisions
into
EnergyPlus commands.
Example
Setpoint

22°C

↓

EnergyPlus
________________________________________
Module 7
Health Engine
Computes
equipment health.
Formula
Health depends on
•	runtime 
•	overload 
•	cycling 
•	efficiency 
•	abnormal power 
Produces
AHU

95%

Pump

81%

Fan

72%

Chiller

90%
This module is unique.
EnergyPlus does not provide this.
________________________________________
Module 8
Digital Twin
One of our strongest presentation components.
Instead of graphs
Provide
interactive building visualization.
________________________________________
Room View
Floor

Office

🟢

Conference

🔴

Lobby

🟢

Meeting

🟡
Click room
Shows
Temperature
Humidity
Occupancy
Energy
Comfort
AI decision
________________________________________
Equipment View
Pump

🟡

Fan

🔴

AHU

🟢
Click
Pump
Shows
Health
Reason
Recommendation
________________________________________
Timeline
09:10

Occupancy ↑

↓

Temperature ↑

↓

Pump Health ↓

↓

AI switched airflow

↓

Comfort restored
________________________________________
Module 9
Dashboard
Sections
________________________________________
Live Metrics
Building Vital Index
Energy
Carbon
Comfort
Equipment Health
________________________________________
Charts
Temperature
Energy
Carbon
Occupancy
Equipment Health
________________________________________
AI Panel
Current Goal
Reason
Confidence
Expected Savings
Expected Comfort
________________________________________
Savings
Energy Saved
Carbon Saved
Predicted Cost Saving
Maintenance Saving
________________________________________
Alerts
Equipment
Comfort
Sensor
Weather
________________________________________
7. Complete Closed Loop
EnergyPlus

↓

Sensors

↓

Python API

↓

MCP Server

↓

Agent Council

↓

Supervisor

↓

Safety Validator

↓

Forward Controller

↓

EnergyPlus

↓

Dashboard

↓

Repeat
This satisfies Honeywell's
Closed Loop Requirement.
________________________________________
8. Demonstration Scenario
Start
Normal building.
↓
Conference room fills.
↓
Temperature increases.
↓
Pump efficiency decreases.
↓
Energy increases.
↓
AI detects all changes.
↓
Energy Agent
Suggests increasing HVAC.
↓
Health Agent
Suggests switching pumps.
↓
Comfort Agent
Requests more airflow.
↓
Carbon Agent
Suggests delaying cooling in unoccupied rooms.
↓
Supervisor combines recommendations.
↓
Safety Validator approves.
↓
EnergyPlus updates.
↓
Digital Twin updates.
↓
Dashboard shows
Energy ↓
Comfort maintained
Equipment protected
Carbon ↓
________________________________________
9. Folder Structure
SentinelAI/

backend/

energyplus/

mcp/

agents/

energy_agent.py

comfort_agent.py

health_agent.py

carbon_agent.py

supervisor.py

validator.py

controller.py

dashboard/

frontend/

digital_twin/

health_engine/

database/

building/

small_office.idf

weather/

docs/

architecture.md

README.md

video/

presentation/











I actually think this is the best approach. Don't delete anything from the current blueprint. Just append this as a "Version 2.0 Architectural Revisions" section at the end. It clearly documents what changed and why, and it also shows judges (or mentors) that the design evolved thoughtfully.
________________________________________
Appendix A – Version 2.0 Architectural Revisions
Overview
Following a detailed architectural review, SentinelAI Version 2.0 introduces several improvements to enhance implementation feasibility, system robustness, explainability, and alignment with the hackathon evaluation criteria. These revisions preserve the original vision of an autonomous AI-driven Building Management System while simplifying implementation and strengthening closed-loop autonomy.
________________________________________
1. Agent Council Implementation Revision
Previous Design
The original design proposed four independent AI agents:
•	Energy Agent
•	Comfort Agent
•	Carbon Agent
•	Health Agent
Each agent independently generated recommendations before passing them to the Supervisor Agent.
________________________________________
Revised Design
The Agent Council remains the core reasoning engine but is implemented as a single structured-output LLM call during each control cycle.
Instead of invoking multiple LLMs or multiple sequential prompts, one prompt requests reasoning from four logical perspectives:
•	Energy Optimization
•	Occupant Comfort
•	Carbon Reduction
•	Equipment Health
The response follows a predefined JSON schema containing individual reasoning sections together with a final recommended action.
Example structure:
{
  "energy": "...",
  "comfort": "...",
  "carbon": "...",
  "health": "...",
  "recommended_action": {
      "temperature":22,
      "airflow":0.75,
      "lighting":"80%"
  }
}
The Supervisor Agent then validates and prioritizes these recommendations before forwarding them to the Safety Validator.
________________________________________
Benefits
•	Lower latency
•	Reduced token usage
•	Fewer API calls
•	More deterministic behavior
•	Easier debugging
•	Better synchronization between objectives
________________________________________
Future Scope
True parallel multi-agent execution remains a future enhancement once the single-call architecture has been fully validated.
________________________________________
2. Safety Validator Enhancement
Previous Design
The Safety Validator simply accepted or rejected the decision generated by the AI.
________________________________________
Revised Design
The Safety Validator has been upgraded into a self-correcting decision loop.
New workflow:
Agent Council
        │
        ▼
Safety Validator
        │
 ┌───────────────┐
 │               │
Valid        Invalid
 │               │
Execute    Return rejection reason
                 │
                 ▼
      Agent Council (Retry)
                 │
        ┌────────┴────────┐
        │                 │
      Valid           Invalid
        │                 │
     Execute     Last Known Good
If the first recommendation violates safety or comfort constraints:
1.	The validator identifies the violated rule.
2.	The rejection reason is appended to the prompt.
3.	The Agent Council performs one additional reasoning cycle.
4.	If the second recommendation is still invalid, the system automatically falls back to the previously verified control state.
________________________________________
Advantages
•	Demonstrates autonomous self-correction
•	Prevents unsafe building operation
•	Eliminates repeated invalid actions
•	Increases robustness
•	Better satisfies the "Agentic Autonomy" evaluation criterion
________________________________________
3. State Manager Module (New)
A dedicated State Manager module has been introduced.
Responsibilities include:
•	Reading EnergyPlus outputs
•	Collecting weather information
•	Collecting occupancy information
•	Aggregating equipment telemetry
•	Preparing the current building state
Instead of every module independently reading simulation variables, the State Manager becomes the single source of truth for all building data.
________________________________________
4. Rolling Context Builder (New)
Rather than sending raw EnergyPlus simulation output to the LLM, SentinelAI now constructs a compact context representation.
Each reasoning cycle includes:
Current State
•	Zone temperatures
•	Humidity
•	PMV
•	Occupancy
•	HVAC power
•	Equipment health
•	Weather
Historical Summary
Rolling window of the previous 10 control intervals including:
•	Minimum temperature
•	Maximum temperature
•	Average temperature
•	Energy trend
•	Comfort trend
•	Carbon trend
•	Equipment health trend
Only summarized information is sent to the LLM.
________________________________________
Advantages
•	Smaller prompts
•	Faster inference
•	Lower memory usage
•	More stable reasoning
•	Avoids exceeding context limits
________________________________________
5. Baseline Comparison Framework
The evaluation framework has been redesigned to compare two complete simulations.
Baseline Simulation
Original EnergyPlus building
No AI modifications
baseline.idf
________________________________________
SentinelAI Simulation
AI-controlled building
sentinel.idf
Both simulations record identical metrics including:
•	Energy consumption
•	PMV
•	Carbon emissions
•	HVAC runtime
•	Equipment health
•	Indoor Air Quality
•	Cost estimation
The Dashboard compares both datasets in real time.
Example metrics include:
•	Energy Saved (%)
•	Carbon Reduction (%)
•	Comfort Improvement
•	Equipment Stress Reduction
•	Estimated Cost Savings
This ensures all reported improvements are based on measured simulation data rather than theoretical estimates.
________________________________________
6. Data Logging Enhancement
SQLite logging has been expanded.
The following tables are maintained:
BuildingState
Stores every simulation timestep.
AgentDecision
Stores every AI recommendation.
ValidatorLog
Stores validation results.
EquipmentHealth
Stores historical health scores.
BaselineMetrics
Stores baseline simulation outputs.
AISimulationMetrics
Stores AI-controlled simulation outputs.
This enables:
•	Historical analytics
•	Decision replay
•	Dashboard visualization
•	Performance benchmarking
________________________________________
7. Revised Closed-Loop Control Pipeline
The autonomous control loop has been updated as follows:
Weather API
        │
Occupancy Schedule
        │
EnergyPlus Simulation
        │
Python Runtime
        │
State Manager
        │
Rolling Context Builder
        │
MCP Tool Server
        │
──────────────────────────────────────────────
Single Structured Agent Council

• Energy Reasoning
• Comfort Reasoning
• Carbon Reasoning
• Health Reasoning

↓

Recommended Action
──────────────────────────────────────────────
        │
Supervisor Agent
        │
Safety Validator
        │
 ┌───────────────┐
 │               │
Valid        Invalid
 │               │
Execute   Retry Agent Council (1 Attempt)
                 │
        ┌────────┴────────┐
        │                 │
      Valid         Last Known Good
        │
Forward Controller
        │
EnergyPlus
        │
SQLite Logger
        │
Baseline Comparator
        │
Dashboard
        │
Digital Twin
________________________________________
8. Revised Development Roadmap
The implementation priority has been updated to reduce integration risk.
Phase 1
Core EnergyPlus control loop
EnergyPlus
↓

Python

↓

MCP

↓

LLM

↓

EnergyPlus
________________________________________
Phase 2
Safety Validator
•	Retry mechanism
•	Last-known-good fallback
________________________________________
Phase 3
Baseline comparison
•	Dual simulation execution
•	Metric logging
•	Dashboard comparison
________________________________________
Phase 4
Equipment Health Engine
•	Health Score
•	Stress Index
•	Remaining Useful Life
•	Failure Probability
________________________________________
Phase 5
Dashboard
________________________________________
Phase 6
Digital Twin
________________________________________
Phase 7
Presentation and Demo
________________________________________
9. Architectural Philosophy Update
SentinelAI is no longer viewed as a collection of independent optimization modules.
Instead, the system follows a layered autonomous architecture consisting of:
1.	Perception Layer
o	EnergyPlus
o	Weather
o	Occupancy
o	Equipment Telemetry
2.	State Management Layer
o	State Manager
o	Rolling Context Builder
3.	Reasoning Layer
o	Structured Agent Council
4.	Decision Layer
o	Supervisor Agent
5.	Safety Layer
o	Safety Validator
o	Retry Mechanism
o	Last Known Good Recovery
6.	Execution Layer
o	Forward Controller
o	EnergyPlus
7.	Evaluation Layer
o	SQLite Logger
o	Baseline Comparator
o	Dashboard
o	Digital Twin
This layered design improves modularity, maintainability, and extensibility while remaining feasible for implementation within the hackathon timeline.
________________________________________
10. Summary of Version 2.0 Improvements
Area	Version 1.0	Version 2.0
Agent Council	Multiple conceptual agents	Single structured LLM call with four reasoning sections
Supervisor	Merge multiple agent outputs	Merge structured council output
Safety Validator	Accept / Reject	Self-correcting retry + fallback
Context	Raw EnergyPlus variables	Rolling summarized context
State Handling	Direct module access	Dedicated State Manager
Logging	Basic history	Full simulation, AI, validator, and baseline logging
Evaluation	Dashboard metrics	Real baseline vs AI comparison
Closed Loop	Observe → Act	Observe → Reason → Validate → Retry → Execute → Evaluate
Reliability	Basic validation	Graceful recovery with last-known-good state
Build Strategy	Feature-first	Core loop → Safety → Baseline → Health → UI
________________________________________
Final Design Position
With these revisions, SentinelAI Version 2.0 evolves from an AI-assisted building controller into a robust Autonomous Building Intelligence Platform. The architecture now emphasizes deterministic reasoning, self-correcting decision-making, measurable performance improvements, and production-inspired software engineering practices while remaining practical for a hackathon implementation. This revised design strengthens the project's alignment with the judging criteria for System Integration, Energy Efficiency, Agentic Autonomy, Reliability, and Presentation Quality.

One small thing worth deciding before you write code, not after: your State Manager is now the single source of truth feeding both the Rolling Context Builder and the SQLite Logger. Make sure it writes to the DB and hands off to the context builder in the same step — if those two paths read EnergyPlus independently at slightly different timesteps, your dashboard numbers and what the LLM reasoned over can drift apart, which is subtle to debug once agents are also in the loop. Just have State Manager produce one state object per cycle and pass that same object everywhere downstream.