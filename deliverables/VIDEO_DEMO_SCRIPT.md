# SentinelAI: 3-Minute Demonstration Video Script

This script is designed to help you quickly record the 3-minute PoC demonstration video required for your submission, proving that the closed-loop control system, LLM integration, and EnergyPlus backend all work together live.

## 🎬 Prep Work Before Recording
1. Open two terminal windows.
2. In Terminal 1, run the FastAPI server: `python -m backend.api.main`
3. Open your browser to `http://localhost:8000` (The SentinelAI Dashboard).
4. Have your code editor open in the background (showing `backend/agents/council.py` or `runner.py`).
5. Ensure your screen recording software is ready.

---

## ⏱️ Video Script (Target: 3 Minutes)

### 0:00 - 0:30 | Introduction & Architecture Overview
* **Action:** Start recording. Show your code editor briefly, then switch to the browser showing the SentinelAI Dashboard.
* **Voiceover:** "Hello, this is the SentinelAI Autonomous Building Intelligence platform. Our solution features a unified Python codebase that integrates an EnergyPlus C-API wrapper, an LLM agent orchestration logic, and a Model Context Protocol communication bus. On the screen, you can see our Live Dashboard which pulls data directly from the EnergyPlus engine via SQLite."

### 0:30 - 1:30 | Triggering the Live Closed-Loop Process
* **Action:** Click the **"▶ Execute Step"** button on the Dashboard.
* **Voiceover:** "I am now triggering a live simulation step. In the background, the system is extracting the current physical state from EnergyPlus—temperatures, CO2, and occupancy—and passing it to our LLM Agent Council. We manage prompt latency by streaming the LLM's JSON response and only providing a compressed rolling-context summary rather than massive raw simulation logs."
* **Action:** *Wait for the floating confirmation bubble to appear.*
* **Voiceover:** "Here we see the Human-in-the-Loop MCP interface. The LLM has generated a structured JSON payload of Actuation Tool Calls based on its safety-validated reasoning. It proposes modifying the setpoints and airflows to optimize comfort and energy."

### 1:30 - 2:15 | Executing the Action & Dashboard Updates
* **Action:** Click **"Approve & Apply Settings"** in the popup.
* **Voiceover:** "Once approved, these parameters are passed back through our MCP Actuator tools directly into the EnergyPlus C memory pointers. The physics engine simulates the next 15 minutes, and the dashboard immediately updates to reflect the new thermal state and equipment health."
* **Action:** Hover over the timeline chart and the 3D floor plan to show the new data points.

### 2:15 - 3:00 | Quantitative Savings Proof
* **Action:** Scroll down to the **"Baseline vs AI Savings"** section of the dashboard (or show your Dual Simulation output logs).
* **Voiceover:** "To explicitly prove our efficiency, we run a dual-simulation framework. Compared to a standard static-schedule baseline, SentinelAI achieves a demonstrable percentage reduction in total kWh consumed. As you can see on the savings dashboard, we significantly cut chiller and fan power consumption while strictly maintaining the indoor PMV thermal comfort boundaries."
* **Action:** Stop recording. 

---
*Good luck with your submission!*
