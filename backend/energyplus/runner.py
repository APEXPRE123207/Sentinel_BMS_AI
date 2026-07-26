"""
SentinelAI - EnergyPlus Interface (Phase 1 Integration Complete)
Provides the EnergyPlus-backed simulation interface used by the control loop.

Both expose the same interface:
    step()           -> Dict[str, Any]   (advance simulation by one timestep)
    apply_actuators( setpoints, airflows, lighting, ventilation, pump_switch )
"""
import sys
import os
import math
import threading
import queue
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# ── Auto-detect EnergyPlus install path ──────────────────────────────────────
_EP_CANDIDATE_PATHS = [
    r"D:\EnergyPlus",
    r"C:\EnergyPlus",
    r"C:\EnergyPlusV24-1-0",
    r"C:\EnergyPlusV23-2-0",
    r"C:\EnergyPlusV22-2-0",
]

def _add_energyplus_to_path() -> Optional[str]:
    for p in _EP_CANDIDATE_PATHS:
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
            logger.info(f"EnergyPlus path added: {p}")
            return p
    return None

_add_energyplus_to_path()


class SimulationEngine:
    """
    Legacy deterministic simulator retained only for backward compatibility.
    The public project path uses EnergyPlusRunner exclusively.
    """

    def __init__(self, is_baseline: bool = False):
        self.is_baseline = is_baseline
        self.timestep = 0
        self.outdoor_temp = 25.0
        self.outdoor_humidity = 50.0
        self.grid_carbon_intensity = float(os.environ.get("SENTINEL_GRID_CARBON_INTENSITY", "0.45"))

        self.zones = {
            "Office": {
                "temperature": 23.0,
                "target_setpoint": 20.0 if self.is_baseline else 22.0,
                "humidity": 50.0,
                "co2": 420.0,
                "pmv": 0.2,
                "occupancy": 8,
                "airflow": 1.0 if self.is_baseline else 0.5,
                "lighting_level": 1.0 if self.is_baseline else 0.8,
            },
            "ConferenceRoom": {
                "temperature": 24.5,
                "target_setpoint": 20.0 if self.is_baseline else 22.0,
                "humidity": 55.0,
                "co2": 750.0,
                "pmv": 0.6,
                "occupancy": 15,
                "airflow": 1.0 if self.is_baseline else 0.6,
                "lighting_level": 1.0,
            },
            "Lobby": {
                "temperature": 23.5,
                "target_setpoint": 20.0 if self.is_baseline else 23.0,
                "humidity": 48.0,
                "co2": 450.0,
                "pmv": 0.3,
                "occupancy": 4,
                "airflow": 1.0 if self.is_baseline else 0.4,
                "lighting_level": 1.0 if self.is_baseline else 0.6,
            },
        }
        self.equipment = {
            "ahu_status": "NORMAL",
            "ahu_health": 98.0,
            "pump_status": "NORMAL",
            "pump_health": 78.0,
            "fan_status": "NORMAL",
            "fan_health": 95.0,
            "chiller_status": "NORMAL",
            "chiller_health": 92.0,
            "total_power_kw": 24.6 if self.is_baseline else 15.2,
            "cumulative_runtime_hours": 145.0,
            "cycling_count": 12,
        }
        self.total_energy_kwh = 0.0
        self.carbon_emissions_kg = 0.0

    def start(self):
        return None

    def stop(self):
        return None

    def apply_actuators(self, setpoints, airflows, lighting, ventilation=None, pump_switch=False):
        for z_id in self.zones:
            if z_id in setpoints:
                self.zones[z_id]["target_setpoint"] = setpoints[z_id]
            if z_id in airflows:
                self.zones[z_id]["airflow"] = airflows[z_id]
            if z_id in lighting:
                self.zones[z_id]["lighting_level"] = lighting[z_id]

        if pump_switch:
            self.equipment["pump_health"] = min(100.0, self.equipment["pump_health"] + 15.0)
            self.equipment["pump_status"] = "REGENERATED"

    def step(self) -> Dict[str, Any]:
        self.timestep += 1
        hour = (self.timestep * 0.25) % 24
        self.outdoor_temp = 24.0 + 5.0 * math.sin((hour - 8) * math.pi / 12)
        self.outdoor_humidity = 50.0 + 10.0 * math.cos(hour * math.pi / 12)

        total_power = 0.0
        for z_id, z in self.zones.items():
            heat_gain = (self.outdoor_temp - z["temperature"]) * 0.08 + z["occupancy"] * 0.12 + z["lighting_level"] * 0.5
            cooling = z["airflow"] * (z["temperature"] - (z["target_setpoint"] - 2.0)) * 0.35
            z["temperature"] = round(z["temperature"] + heat_gain - cooling, 2)
            z["pmv"] = round(max(-3.0, min(3.0, (z["temperature"] - 22.0) * 0.35 + (z["occupancy"] - 5) * 0.02)), 2)
            z["co2"] = round(max(400.0, z["co2"] + z["occupancy"] * 12.0 - z["airflow"] * 150.0), 1)

            chiller_work = z["airflow"] * max(0, self.outdoor_temp - (z["target_setpoint"] - 2.0)) * 0.5
            total_power += (z["airflow"] * 3.5) + chiller_work

        total_power += 5.0
        self.equipment["total_power_kw"] = round(total_power, 2)
        self.equipment["cumulative_runtime_hours"] += 0.25
        if total_power > 25.0:
            self.equipment["pump_health"] = max(0.0, self.equipment["pump_health"] - 0.2)
            self.equipment["fan_health"] = max(0.0, self.equipment["fan_health"] - 0.1)

        step_energy = total_power * 0.25
        self.total_energy_kwh = round(self.total_energy_kwh + step_energy, 3)
        self.carbon_emissions_kg = round(self.carbon_emissions_kg + step_energy * self.grid_carbon_intensity, 3)

        return {
            "timestep": self.timestep,
            "outdoor_temp": round(self.outdoor_temp, 2),
            "outdoor_humidity": round(self.outdoor_humidity, 2),
            "grid_carbon_intensity": self.grid_carbon_intensity,
            "zones": self.zones,
            "equipment": self.equipment,
            "total_energy_kwh": self.total_energy_kwh,
            "carbon_emissions_kg": self.carbon_emissions_kg,
        }


# =============================================================================
# 1. BUILT-IN SIMULATION ENGINE (fallback / unit testing)
# =============================================================================
# class SimulationEngine:
#     """
#     Multi-Zone Building Physics Simulation Engine.
#     Simulates thermal dynamics, occupant loads, HVAC power, equipment stress,
#     and outdoor weather. Used as a fast fallback when EnergyPlus is not running.
#     """
#     def __init__(self, is_baseline: bool = False):
#         self.is_baseline = is_baseline
#         self.timestep = 0
#         self.outdoor_temp = 25.0
#         self.outdoor_humidity = 50.0
# 
#         # Initialize BOTH models with the exact same physical starting state for fair comparison
#         self.zones = {
#             "Office": {
#                 "temperature": 23.0, "target_setpoint": 20.0 if self.is_baseline else 22.0,
#                 "humidity": 50.0, "co2": 420.0, "pmv": 0.2,
#                 "occupancy": 8, "airflow": 1.0 if self.is_baseline else 0.5, "lighting_level": 1.0 if self.is_baseline else 0.8
#             },
#             "ConferenceRoom": {
#                 "temperature": 24.5, "target_setpoint": 20.0 if self.is_baseline else 22.0,
#                 "humidity": 55.0, "co2": 750.0, "pmv": 0.6,
#                 "occupancy": 15, "airflow": 1.0 if self.is_baseline else 0.6, "lighting_level": 1.0
#             },
#             "Lobby": {
#                 "temperature": 23.5, "target_setpoint": 20.0 if self.is_baseline else 23.0,
#                 "humidity": 48.0, "co2": 450.0, "pmv": 0.3,
#                 "occupancy": 4, "airflow": 1.0 if self.is_baseline else 0.4, "lighting_level": 1.0 if self.is_baseline else 0.6
#             },
#         }
#         self.equipment = {
#             "ahu_status": "NORMAL", "ahu_health": 98.0,
#             "pump_status": "NORMAL", "pump_health": 78.0,
#             "fan_status": "NORMAL", "fan_health": 95.0,
#             "chiller_status": "NORMAL", "chiller_health": 92.0,
#             "total_power_kw": 24.6 if self.is_baseline else 15.2,
#             "cumulative_runtime_hours": 145.0,
#             "cycling_count": 12,
#         }
#         self.total_energy_kwh = 0.0
#         self.carbon_emissions_kg = 0.0
# 
#     def reset(self):
#         """Resets simulation engine state back to initial step 0 state."""
#         self.__init__(is_baseline=getattr(self, "is_baseline", False))
# 
#     def apply_actuators(self, setpoints, airflows, lighting,
#                         ventilation=None, pump_switch=False):
#         for z_id in self.zones:
#             if z_id in setpoints:
#                 self.zones[z_id]["target_setpoint"] = setpoints[z_id]
#             if z_id in airflows:
#                 self.zones[z_id]["airflow"] = airflows[z_id]
#             if z_id in lighting:
#                 self.zones[z_id]["lighting_level"] = lighting[z_id]
#         if pump_switch:
#             self.equipment["pump_health"] = min(100.0, self.equipment["pump_health"] + 15.0)
#             self.equipment["pump_status"] = "REGENERATED"
# 
#     def step(self) -> Dict[str, Any]:
#         self.timestep += 1
#         hour = (self.timestep * 0.25) % 24
#         self.outdoor_temp = 24.0 + 5.0 * math.sin((hour - 8) * math.pi / 12)
#         self.outdoor_humidity = 50.0 + 10.0 * math.cos(hour * math.pi / 12)
# 
#         total_power = 0.0
#         for z_id, z in self.zones.items():
#             heat_gain = (self.outdoor_temp - z["temperature"]) * 0.08 + z["occupancy"] * 0.12 + z["lighting_level"] * 0.5
#             cooling = z["airflow"] * (z["temperature"] - (z["target_setpoint"] - 2.0)) * 0.35
#             z["temperature"] = round(z["temperature"] + heat_gain - cooling, 2)
#             z["pmv"] = round(max(-3.0, min(3.0, (z["temperature"] - 22.0) * 0.35 + (z["occupancy"] - 5) * 0.02)), 2)
#             z["co2"] = round(max(400.0, z["co2"] + z["occupancy"] * 12.0 - z["airflow"] * 150.0), 1)
#             
#             # Fan power + Chiller power (cooling outdoor air to supply temp)
#             chiller_work = z["airflow"] * max(0, self.outdoor_temp - (z["target_setpoint"] - 2.0)) * 0.5
#             total_power += (z["airflow"] * 3.5) + chiller_work
# 
#         total_power += 5.0
#         self.equipment["total_power_kw"] = round(total_power, 2)
#         self.equipment["cumulative_runtime_hours"] += 0.25
#         if total_power > 25.0:
#             self.equipment["pump_health"] = max(0.0, self.equipment["pump_health"] - 0.2)
#             self.equipment["fan_health"] = max(0.0, self.equipment["fan_health"] - 0.1)
# 
#         step_energy = total_power * 0.25
#         self.total_energy_kwh = round(self.total_energy_kwh + step_energy, 3)
#         self.carbon_emissions_kg = round(self.carbon_emissions_kg + step_energy * 0.45, 3)
# 
#         return {
#             "timestep": self.timestep,
#             "outdoor_temp": round(self.outdoor_temp, 2),
#             "outdoor_humidity": round(self.outdoor_humidity, 2),
#             "zones": self.zones,
#             "equipment": self.equipment,
#             "total_energy_kwh": self.total_energy_kwh,
#             "carbon_emissions_kg": self.carbon_emissions_kg,
#         }
# 
# 
# # =============================================================================
# =============================================================================
# 2. REAL ENERGYPLUS RUNNER (pyenergyplus.api)
# =============================================================================
# Default paths (relative to this file's location)
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_IDF = os.path.join(_HERE, "..", "building", "small_office.idf")
_DEFAULT_EPW = os.path.join(_HERE, "..", "building", "weather.epw")

class EnergyPlusRunner:
    """
    Real EnergyPlus simulation runner using pyenergyplus.api.
    Runs EnergyPlus in a background thread and exposes a step() / apply_actuators()
    interface used by the control loop.

    How it works:
      - EnergyPlus runs in a daemon thread.
      - At every zone timestep, a callback fires.  It reads sensor variables,
        writes actuator values, then puts the state snapshot onto self._state_queue.
      - step() blocks until the next snapshot arrives (or returns stale data on timeout).
    """
    # Zone name mapping: SentinelAI logical name -> EnergyPlus zone name in IDF
    # These must EXACTLY match the Zone names declared in small_office.idf (case-sensitive)
    ZONE_MAP: Dict[str, str] = {
        "Office":         "West Zone",
        "ConferenceRoom": "EAST ZONE",
        "Lobby":          "NORTH ZONE",
    }

    ZONE_MAX_OCCUPANCY: Dict[str, int] = {
        "Office": 8,
        "ConferenceRoom": 15,
        "Lobby": 2,
    }

    def __init__(
        self,
        idf_path: str = _DEFAULT_IDF,
        epw_path: str = _DEFAULT_EPW,
        ep_install_dir: str = r"D:\EnergyPlus",
    ):
        self.idf_path = os.path.abspath(idf_path)
        self.epw_path = os.path.abspath(epw_path)
        self.ep_install_dir = ep_install_dir

        self._api = None
        self._ep_state = None                    # EnergyPlus internal state handle
        self._state_queue: queue.Queue = queue.Queue(maxsize=1)
        self._actuator_values: Dict[str, Any] = {}  # zone_id -> {setpoint, airflow, …}
        self._actuator_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._timestep = 0
        self._cumulative_energy_kwh = 0.0
        self._cumulative_carbon_kg = 0.0
        self._grid_carbon_intensity = float(os.environ.get("SENTINEL_GRID_CARBON_INTENSITY", "0.45"))
        self._cumulative_runtime_hours = 0.0
        self._cycling_count = 0
        self._prev_power_kw = 0.0
        self._occupancy_start_hour = float(os.environ.get("SENTINEL_START_HOUR", "6.75"))

        # Equipment health (tracked by SentinelAI, not by EnergyPlus)
        self._equipment_health = {
            "ahu_health": 98.0, "ahu_status": "NORMAL",
            "pump_health": 78.0, "pump_status": "NORMAL",
            "fan_health": 95.0, "fan_status": "NORMAL",
            "chiller_health": 92.0, "chiller_status": "NORMAL",
        }

        # Lockstep synchronization events
        self._step_done = threading.Event()
        self._step_proceed = threading.Event()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def start(self):
        """Initialize API, create EP state handle, and launch simulation thread."""
        if ep_install_dir := self.ep_install_dir:
            if ep_install_dir not in sys.path:
                sys.path.insert(0, ep_install_dir)

        try:
            from pyenergyplus.api import EnergyPlusAPI
        except ImportError as e:
            raise RuntimeError(
                f"Could not import pyenergyplus. Make sure EnergyPlus is installed at "
                f"{self.ep_install_dir}.\n  Error: {e}"
            )

        self._api = EnergyPlusAPI()
        self._ep_state = self._api.state_manager.new_state()

        # Suppress EnergyPlus console output
        self._api.runtime.set_console_output_status(self._ep_state, False)

        # Register callbacks
        self._api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
            self._ep_state, self._timestep_callback
        )

        self._running = True
        self._step_done.clear()
        self._step_proceed.clear()

        self._thread = threading.Thread(target=self._run_ep, daemon=True, name="EnergyPlus")
        self._thread.start()
        logger.info(f"EnergyPlus simulation thread started. IDF: {self.idf_path}")

    def stop(self):
        """Request EnergyPlus to stop and wait for the thread."""
        self._running = False
        self._step_proceed.set()  # Unblock callback if waiting
        if self._api and self._ep_state:
            try:
                self._api.runtime.stop_simulation(self._ep_state)
            except Exception:
                pass
        
        # Block until the background thread completely exits so it can't write to DB
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._thread:
            self._thread.join(timeout=10)

    def apply_actuators(
        self,
        setpoints: Dict[str, float],
        airflows: Dict[str, float],
        lighting: Dict[str, float],
        ventilation: Optional[float] = None,
        pump_switch: bool = False,
    ):
        """Queue actuator commands.  They are applied in the next EP callback."""
        with self._actuator_lock:
            self._actuator_values = {
                "setpoints": setpoints,
                "airflows": airflows,
                "lighting": lighting,
                "ventilation": ventilation,
                "pump_switch": pump_switch,
            }
        if pump_switch:
            self._equipment_health["pump_health"] = min(
                100.0, self._equipment_health["pump_health"] + 15.0
            )
            self._equipment_health["pump_status"] = "REGENERATED"

    def step(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Advances EnergyPlus by exactly 1 timestep in lockstep.
        Blocks until EnergyPlus delivers the timestep snapshot.
        """
        # Clear the done flag FIRST, so we guarantee we wait for the next step's completion
        self._step_done.clear()
        
        # Signal EnergyPlus thread to proceed with 1 timestep
        self._step_proceed.set()
        
        # Wait for EnergyPlus to complete exactly 1 timestep
        if self._step_done.wait(timeout=timeout):
            try:
                snapshot = self._state_queue.get_nowait()
                self._last_snapshot = snapshot
                return snapshot
            except queue.Empty:
                pass

        logger.warning("EnergyPlus step() timed out — returning last known state.")
        return getattr(self, "_last_snapshot", self._empty_snapshot())

    # ------------------------------------------------------------------
    # Private — EnergyPlus thread
    # ------------------------------------------------------------------
    def _run_ep(self):
        output_dir = os.path.join(os.path.dirname(self.idf_path), "ep_output")
        os.makedirs(output_dir, exist_ok=True)
        args = [
            "-w", self.epw_path,
            "-d", output_dir,
            self.idf_path,
        ]
        try:
            exit_code = self._api.runtime.run_energyplus(self._ep_state, args)
            if exit_code != 0:
                logger.error(f"EnergyPlus exited with code {exit_code}")
        except OSError as exc:
            logger.info(f"EnergyPlus runtime ended: {exc}")
        self._running = False

    def _timestep_callback(self, ep_state):
        """Called by EnergyPlus at every zone-timestep. Reads state, writes actuators."""
        if not self._running:
            return
        
        api = self._api
        if not api.exchange.api_data_fully_ready(ep_state):
            return
            
        self._timestep += 1
        sim_hour = (self._occupancy_start_hour + (self._timestep - 1) * 0.25) % 24.0

        def _occupancy_fraction(hour: float) -> float:
            if hour < 6.0:
                return 0.0
            if hour < 7.0:
                return 0.10
            if hour < 8.0:
                return 0.50
            if hour < 12.0:
                return 1.00
            if hour < 13.0:
                return 0.50
            if hour < 16.0:
                return 1.00
            if hour < 17.0:
                return 0.50
            if hour < 18.0:
                return 0.10
            return 0.0

        # ── Apply pending actuator commands ──────────────────────────
        with self._actuator_lock:
            cmds = dict(self._actuator_values)

        setpoints = cmds.get("setpoints", {})
        for sentinel_zone, ep_zone in self.ZONE_MAP.items():
            if sentinel_zone in setpoints:
                try:
                    # Cooling setpoint actuator — standard EnergyPlus thermostat control
                    cool_handle = api.exchange.get_actuator_handle(
                        ep_state,
                        "Zone Temperature Control",
                        "Cooling Setpoint",
                        ep_zone,
                    )
                    heat_handle = api.exchange.get_actuator_handle(
                        ep_state,
                        "Zone Temperature Control",
                        "Heating Setpoint",
                        ep_zone,
                    )
                    sp = setpoints[sentinel_zone]
                    if cool_handle != -1:
                        api.exchange.set_actuator_value(ep_state, cool_handle, sp)
                    if heat_handle != -1:
                        api.exchange.set_actuator_value(ep_state, heat_handle, max(19.0, sp - 2.0))
                except Exception as e:
                    logger.debug(f"Actuator set failed for {ep_zone}: {e}")

        # ── Read zone state variables ─────────────────────────────────
        zones_data: Dict[str, Dict[str, Any]] = {}
        total_power_kw = 0.0

        for sentinel_zone, ep_zone in self.ZONE_MAP.items():
            def _get(var_type, var_key, unit=""):
                try:
                    # TEACHING MOMENT: How EnergyPlus variables enter Python
                    # 1. The IDF file must explicitly declare "Output:Variable" for the data we want.
                    # 2. We ask the C API for a "handle" (an integer memory address) to that variable for a specific zone.
                    handle = api.exchange.get_variable_handle(ep_state, var_type, var_key)
                    # 3. We use that handle to efficiently read the current float value from the C engine memory.
                    return api.exchange.get_variable_value(ep_state, handle) if handle != -1 else 0.0
                except Exception:
                    return 0.0

            temp = _get("Zone Mean Air Temperature", ep_zone)
            humidity = _get("Zone Air Relative Humidity", ep_zone)
            co2 = _get("Zone Air CO2 Concentration", ep_zone)
            people = _get("Zone People Occupant Count", ep_zone)

            max_people = self.ZONE_MAX_OCCUPANCY.get(sentinel_zone, int(round(people)) if people else 0)
            schedule_people = int(round(max_people * _occupancy_fraction(sim_hour)))
            if schedule_people > 0:
                schedule_people = max(1, schedule_people)

            # PMV approximation (EnergyPlus may not expose it directly via API)
            pmv = round(max(-3.0, min(3.0, (temp - 22.0) * 0.35 + (schedule_people - 5) * 0.02)), 2)

            zones_data[sentinel_zone] = {
                "temperature": round(temp, 2),
                "target_setpoint": cmds.get("setpoints", {}).get(sentinel_zone, 22.0),
                "humidity": round(humidity, 1),
                "co2": round(co2, 1),
                "pmv": pmv,
                "occupancy": schedule_people,
                "occupancy_raw": int(people),
                "airflow": cmds.get("airflows", {}).get(sentinel_zone, 0.5),
                "lighting_level": cmds.get("lighting", {}).get(sentinel_zone, 0.8),
            }

        # ── Outdoor weather ───────────────────────────────────────────
        try:
            oa_temp_handle = api.exchange.get_variable_handle(ep_state, "Site Outdoor Air Drybulb Temperature", "Environment")
            oa_hum_handle  = api.exchange.get_variable_handle(ep_state, "Site Outdoor Air Relative Humidity", "Environment")
            outdoor_temp = api.exchange.get_variable_value(ep_state, oa_temp_handle) if oa_temp_handle != -1 else 25.0
            outdoor_humidity = api.exchange.get_variable_value(ep_state, oa_hum_handle) if oa_hum_handle != -1 else 50.0
            # Sanity guard — EP returns 0.0 during pre-warmup
            if outdoor_temp == 0.0:
                outdoor_temp = 25.0
            if outdoor_humidity == 0.0:
                outdoor_humidity = 50.0
        except Exception:
            outdoor_temp = 25.0
            outdoor_humidity = 50.0

        # ── Energy & carbon accumulation ──────────────────────────────
        # Read whole-building electricity demand rate (W) from EnergyPlus
        try:
            elec_handle = -1
            for k in ["Whole Building", "Facility", "Environment", ""]:
                elec_handle = api.exchange.get_variable_handle(
                    ep_state, "Facility Total Electricity Demand Rate", k
                )
                if elec_handle != -1:
                    break

            if elec_handle != -1:
                total_power_kw = api.exchange.get_variable_value(ep_state, elec_handle) / 1000.0  # W → kW
        except Exception:
            pass  # keep last total_power_kw from zone loop

        step_energy = max(0.0, total_power_kw) * 0.25          # 15-min timestep → kWh
        self._cumulative_energy_kwh += step_energy

        self._cumulative_carbon_kg += step_energy * self._grid_carbon_intensity
        self._cumulative_runtime_hours += 0.25

        # Detect cycling (large power swings)
        if abs(total_power_kw - self._prev_power_kw) > 5.0:
            self._cycling_count += 1
        self._prev_power_kw = total_power_kw

        # Equipment health degradation
        eq = self._equipment_health
        if total_power_kw > 25.0:
            eq["pump_health"] = max(0.0, eq["pump_health"] - 0.2)
            eq["fan_health"] = max(0.0, eq["fan_health"] - 0.1)

        equipment_data = {
            **eq,
            "total_power_kw": round(total_power_kw, 2),
            "cumulative_runtime_hours": round(self._cumulative_runtime_hours, 2),
            "cycling_count": self._cycling_count,
        }

        snapshot = {
            "timestep": self._timestep,
            "outdoor_temp": round(outdoor_temp, 2),
            "outdoor_humidity": round(outdoor_humidity, 1),
            "grid_carbon_intensity": self._grid_carbon_intensity,
            "zones": zones_data,
            "equipment": equipment_data,
            "total_energy_kwh": round(self._cumulative_energy_kwh, 3),
            "carbon_emissions_kg": round(self._cumulative_carbon_kg, 3),
        }

        # Put snapshot into queue and signal step() is ready
        try:
            self._state_queue.put_nowait(snapshot)
        except queue.Full:
            try:
                self._state_queue.get_nowait()
            except queue.Empty:
                pass
            self._state_queue.put_nowait(snapshot)

        self._step_done.set()

        # Pause EnergyPlus thread until main thread step() signals proceed
        self._step_proceed.wait(timeout=10.0)
        self._step_proceed.clear()

    def _empty_snapshot(self) -> Dict[str, Any]:
        return {
            "timestep": self._timestep,
            "outdoor_temp": 25.0, "outdoor_humidity": 50.0,
            "zones": {z: {"temperature": 22.0, "target_setpoint": 22.0, "humidity": 50.0,
                          "co2": 400.0, "pmv": 0.0, "occupancy": 0, "airflow": 0.5, "lighting_level": 0.8}
                     for z in self.ZONE_MAP},
            "equipment": {**self._equipment_health, "total_power_kw": 0.0,
                          "cumulative_runtime_hours": 0.0, "cycling_count": 0},
            "total_energy_kwh": 0.0, "carbon_emissions_kg": 0.0,
        }


# =============================================================================
# Legacy alias kept for backward compatibility with existing imports
# =============================================================================
EnergyPlusAPIAdapter = EnergyPlusRunner
