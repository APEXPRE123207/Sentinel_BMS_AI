"""
SentinelAI - Structured Agent Council (v2.0)
Single-call structured agent council that evaluates building context across four core dimensions:
1. Energy Optimization
2. Occupant Comfort
3. Carbon Emissions
4. Equipment Health
Returns structured JSON recommendations containing objective reasoning and control actions.
Includes a robust fallback reasoning engine for offline/standalone execution.
"""
import json
import logging
import os
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
from ..database.models import AgentCouncilDecision, ActionRecommendation

logger = logging.getLogger(__name__)

COUNCIL_SYSTEM_PROMPT = """You are the SentinelAI Agent Council, an autonomous Building Management Intelligence engine for building automation.
You must analyze the building's current state and historical trends from 4 perspectives:
1. ENERGY AGENT: Minimize electrical energy consumption and peak load.
2. COMFORT AGENT: Maintain occupant thermal comfort (PMV near 0, temperature 20-24°C, indoor air quality).
3. CARBON AGENT: Reduce carbon emissions using real-time grid carbon intensity.
4. HEALTH AGENT: Protect equipment (pumps, fans, chillers, AHU) from excessive cycling, thermal stress, or degradation.

You MUST respond strictly with a valid JSON object adhering to this schema:
{
  "energy_reasoning": "Explanation of energy optimization decision",
  "comfort_reasoning": "Explanation of comfort maintenance decision",
  "carbon_reasoning": "Explanation of carbon emission reduction decision",
  "health_reasoning": "Explanation of equipment health protection decision",
  "recommended_action": {
    "zone_setpoints": {
      "Office": float,
      "ConferenceRoom": float,
      "Lobby": float
    },
    "zone_airflows": {
      "Office": float,
      "ConferenceRoom": float,
      "Lobby": float
    },
    "zone_lighting": {
      "Office": float,
      "ConferenceRoom": float,
      "Lobby": float
    },
    "ventilation_rate": float,
    "pump_switch_active": boolean
  }
}
Do not include any extra text outside the JSON object.
"""

class AgentCouncil:
    def __init__(self, api_url: Optional[str] = None, model_name: str = "gemini-flash-latest"):
        self.api_key = None
        self.api_url = api_url
        self.model_name = model_name
        
        import dotenv
        # Load API key and URL from .env if present
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        self.is_ollama_cloud = False
        if os.path.exists(env_path):
            dotenv.load_dotenv(env_path)
            
            ollama_key = os.environ.get("OLLAMA_API_KEY")
            if ollama_key:
                self.api_url = "https://ollama.com/api/chat"
                self.api_key = ollama_key
                self.model_name = "minimax-m3"
                self.is_ollama_cloud = True
                logger.info("AgentCouncil initialized with Ollama Cloud API Key from .env")
            else:
                env_key = os.environ.get("LLM_API_KEY")
                if env_key:
                    if env_key == "0":
                        self.api_url = "http://localhost:11434/v1/chat/completions"
                        self.model_name = "minimax-m3"
                        logger.info("AgentCouncil detected LLM_API_KEY=0. Routing to local Ollama.")
                    else:
                        self.api_key = env_key
                        if not self.api_url:
                            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                        logger.info("AgentCouncil initialized with Cloud API Key from .env")

    def evaluate(
        self,
        context: Dict[str, Any],
        rejection_feedback: Optional[str] = None
    ) -> AgentCouncilDecision:
        """
        Executes the Agent Council reasoning cycle.
        If an external API is specified and reachable, calls the LLM.
        Otherwise, invokes the deterministic rule-based Council engine.
        """
        user_prompt = f"Current Building Context:\n{json.dumps(context, indent=2)}\n"
        if rejection_feedback:
            user_prompt += f"\n[CRITICAL SAFETY FEEDBACK FROM PREVIOUS ATTEMPT]:\n{rejection_feedback}\nAdjust setpoints to satisfy safety limits!\n"

        if self.api_key and self.api_url:
            try:
                decision = self._call_llm_api(user_prompt)
                if decision:
                    return decision
            except Exception as e:
                logger.warning(f"LLM API call failed ({e}). Falling back to deterministic council engine.")

        return self._deterministic_council_engine(context, rejection_feedback)

    def _call_llm_api(self, user_prompt: str) -> Optional[AgentCouncilDecision]:
        system_instruction = "You are the SentinelAI Agent Council, an autonomous Building Management Intelligence engine for building automation.\nYou must analyze the building's current state and historical trends from 4 perspectives:\n1. ENERGY AGENT: Minimize electrical energy consumption and peak load.\n2. COMFORT AGENT: Maintain occupant thermal comfort (PMV near 0, temperature 20-24°C, indoor air quality).\n3. CARBON AGENT: Reduce carbon emissions using real-time grid carbon intensity.\n4. HEALTH AGENT: Protect equipment (pumps, fans, chillers, AHU) from excessive cycling, thermal stress, or degradation.\n\nYou MUST respond strictly with a valid JSON object adhering to this schema:\n{\n  \"energy_reasoning\": \"Explanation of energy optimization decision\",\n  \"comfort_reasoning\": \"Explanation of comfort maintenance decision\",\n  \"carbon_reasoning\": \"Explanation of carbon emission reduction decision\",\n  \"health_reasoning\": \"Explanation of equipment health protection decision\",\n  \"recommended_action\": {\n    \"zone_setpoints\": {\n      \"Office\": float,\n      \"ConferenceRoom\": float,\n      \"Lobby\": float\n    },\n    \"zone_airflows\": {\n      \"Office\": float,\n      \"ConferenceRoom\": float,\n      \"Lobby\": float\n    },\n    \"zone_lighting\": {\n      \"Office\": float,\n      \"ConferenceRoom\": float,\n      \"Lobby\": float\n    },\n    \"ventilation_rate\": float,\n    \"pump_switch_active\": boolean\n  }\n}\nDo not include any extra text outside the JSON object."
        
        is_gemini = "generativelanguage.googleapis.com" in self.api_url
        headers = {"Content-Type": "application/json"}
        
        if is_gemini:
            headers["X-goog-api-key"] = self.api_key
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
            }
        elif getattr(self, "is_ollama_cloud", False):
            headers["Authorization"] = f"Bearer {self.api_key}"
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2}
            }
        else:
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            payload = {
                "model": self.model_name or "minimax-default",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data, headers=headers, method="POST")

        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            
            if is_gemini:
                content = res_json["candidates"][0]["content"]["parts"][0]["text"]
            elif getattr(self, "is_ollama_cloud", False):
                content = res_json["message"]["content"]
            else:
                content = res_json["choices"][0]["message"]["content"]
                
            # Clean markdown code blocks if the model wrapped the JSON
            if content.startswith("```"):
                content = content.strip("`").removeprefix("json").strip()
                
            parsed = json.loads(content)

            rec = parsed.get("recommended_action", {})
            action = ActionRecommendation(
                zone_setpoints=rec.get("zone_setpoints", {}),
                zone_airflows=rec.get("zone_airflows", {}),
                zone_lighting=rec.get("zone_lighting", {}),
                ventilation_rate=rec.get("ventilation_rate", 0.5),
                pump_switch_active=rec.get("pump_switch_active", False)
            )

            return AgentCouncilDecision(
                energy_reasoning=parsed.get("energy_reasoning", ""),
                comfort_reasoning=parsed.get("comfort_reasoning", ""),
                carbon_reasoning=parsed.get("carbon_reasoning", ""),
                health_reasoning=parsed.get("health_reasoning", ""),
                recommended_action=action,
                raw_response=content
            )

    def _deterministic_council_engine(
        self,
        context: Dict[str, Any],
        rejection_feedback: Optional[str] = None
    ) -> AgentCouncilDecision:
        """
        Deterministic Council Engine balancing Energy, Comfort, Carbon, and Health objectives.
        """
        outdoor_temp = context.get("outdoor_temp_c", 25.0)
        zones = context.get("zones", {})
        equipment = context.get("equipment", {})
        pump_health = equipment.get("pump_health_pct", 100.0)

        setpoints = {}
        airflows = {}
        lighting = {}
        energy_notes = [f"Analyzing outdoor ambient conditions ({outdoor_temp:.1f}°C). Balancing HVAC power demand to minimize peak load."]
        comfort_notes = []
        carbon_notes = []
        health_notes = []

        pump_switch = False
        if pump_health < 80.0:
            pump_switch = True
            health_notes.append(f"Pump health degraded ({pump_health}%). Requesting pump rotation.")
        else:
            health_notes.append(f"Equipment health normal (Pump: {pump_health}%).")

        for z_id, z in zones.items():
            occupancy = z.get("occupancy", 0)
            cur_temp = z.get("temp_c", 22.0)
            cur_setpoint = z.get("setpoint_c", 22.0)
            pmv = z.get("pmv", 0.0)

            if occupancy > 0:
                # Occupied room: balance comfort & energy
                desired_target = 22.0  # ASHRAE 55 Standard neutral comfort target
                if cur_temp > 24.0 or pmv > 0.5:
                    airflow = min(1.0, 0.5 + (cur_temp - 24.0) * 0.2)
                    comfort_notes.append(f"Zone {z_id} occupied ({occupancy} people) with high temp ({cur_temp:.1f}°C). Increasing airflow to {round(airflow, 2)}.")
                else:
                    airflow = 0.5
                    comfort_notes.append(f"Zone {z_id} occupied ({occupancy} people). Target setpoint 22.0°C (ASHRAE 55 neutral comfort standard).")

                light_level = 0.9
            else:
                # Unoccupied room: setback temperature for energy & carbon savings
                desired_target = 25.0 if outdoor_temp > 25.0 else 20.0
                airflow = 0.2
                light_level = 0.2
                energy_notes.append(f"Zone {z_id} unoccupied. Setting back setpoint toward {desired_target}°C and airflow to 0.2.")

            # Ramp setpoint smoothly (max 2.0°C step) to satisfy safety rate-of-change limits
            max_ramp_step = 2.0
            target_temp = round(max(cur_setpoint - max_ramp_step, min(cur_setpoint + max_ramp_step, desired_target)), 2)

            setpoints[z_id] = target_temp
            airflows[z_id] = round(airflow, 2)
            lighting[z_id] = light_level

        if outdoor_temp > 28.0:
            carbon_notes.append("High outdoor ambient temperature. Prioritizing demand response smoothing.")
        else:
            carbon_notes.append("Grid carbon intensity stable. Operating within baseline carbon budgets.")

        # If previous safety rejection feedback was received, apply safety corrections (hold current setpoint)
        if rejection_feedback:
            health_notes.append(f"Safety adjustment applied: {rejection_feedback}")
            for z_id in setpoints:
                setpoints[z_id] = zones.get(z_id, {}).get("setpoint_c", 22.0)

        action = ActionRecommendation(
            zone_setpoints=setpoints,
            zone_airflows=airflows,
            zone_lighting=lighting,
            ventilation_rate=0.5,
            pump_switch_active=pump_switch
        )

        return AgentCouncilDecision(
            energy_reasoning="; ".join(energy_notes),
            comfort_reasoning="; ".join(comfort_notes),
            carbon_reasoning="; ".join(carbon_notes),
            health_reasoning="; ".join(health_notes),
            recommended_action=action,
            raw_response="Deterministic Agent Council Execution"
        )
