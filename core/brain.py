# core/brain.py - Standalone LLM Brain for English Coach
import json
import re
from . import config

try:
    from openai import OpenAI
except ImportError:
    pass

class StandaloneBrain:
    """A lightweight brain that handles LLM API clients and JSON parsing."""
    
    def __init__(self):
        self.provider_clients = {}
        self._init_clients()
        pass # print("[OK] Standalone Brain initialized.")

    def _init_clients(self):
        """Initialize LLM provider clients based on config."""
        try:
            for provider, cfg in config.PROVIDER_CONFIGS.items():
                if cfg.get("api_key"):
                    client = OpenAI(api_key=cfg["api_key"], base_url=cfg.get("base_url"))
                    self.provider_clients[provider] = client
        except Exception as e:
            pass # print(f"[BRAIN] Client init error: {e}")

    def _get_client(self, provider):
        """Lazy access/init for clients."""
        return self.provider_clients.get(provider)

    def _parse_json(self, text):
        """Parse JSON robustly from LLM response."""
        if not text or not isinstance(text, str):
            return None
        text = text.strip()
        text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        try:
            return json.loads(text)
        except:
            pass
        # Manual extraction
        try:
            depth = 0
            start = -1
            for i, c in enumerate(text):
                if c == '{':
                    if depth == 0: start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0 and start != -1:
                        try:
                            return json.loads(text[start:i+1])
                        except:
                            continue
        except:
            pass
        return {}
