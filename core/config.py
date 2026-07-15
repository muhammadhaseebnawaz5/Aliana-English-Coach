# core/config.py - Standalone Configuration for English Coach
import os
import json

# ── Paths ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Use AppData/Local for persistent data on Windows, or ~/.alina_coach as fallback
if os.name == 'nt':
    DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AlinaCoach', 'data')
else:
    DATA_DIR = os.path.join(os.path.expanduser('~'), '.alina_coach', 'data')

# Ensure data directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# ── API Keys ─────────────────────────────────────────────
# Keys are loaded from data/api_keys.json (distributed) or environment
API_KEYS_PATH = os.path.join(DATA_DIR, "api_keys.json")

def load_keys():
    defaults = {
        "GROK_API_KEY": "",
        "OPENAI_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "HUGGINGFACE_API_KEY": ""
    }
    if os.path.exists(API_KEYS_PATH):
        try:
            with open(API_KEYS_PATH, "r") as f:
                return {**defaults, **json.load(f)}
        except: pass
    return defaults

KEYS = load_keys()
GROK_API_KEY = KEYS["GROK_API_KEY"]
OPENAI_API_KEY = KEYS["OPENAI_API_KEY"]
OPENROUTER_API_KEY = KEYS["OPENROUTER_API_KEY"]
HUGGINGFACE_API_KEY = KEYS["HUGGINGFACE_API_KEY"]

def save_keys(keys_dict):
    with open(API_KEYS_PATH, "w") as f:
        json.dump(keys_dict, f, indent=4)
    # Reload globals
    global GROK_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, HUGGINGFACE_API_KEY
    GROK_API_KEY = keys_dict.get("GROK_API_KEY", "")
    OPENAI_API_KEY = keys_dict.get("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY = keys_dict.get("OPENROUTER_API_KEY", "")
    HUGGINGFACE_API_KEY = keys_dict.get("HUGGINGFACE_API_KEY", "")

# ── Dynamic Provider Configs ──────────────────────────────
def get_provider_configs():
    return {
        "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key": GROK_API_KEY},
        "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key": OPENROUTER_API_KEY},
        "huggingface": {"base_url": "https://router.huggingface.co/v1", "api_key": HUGGINGFACE_API_KEY}
    }

PROVIDER_CONFIGS = get_provider_configs()

# ── Text Models Chain (Intent Extraction) ────────────────
TEXT_MODELS_CHAIN = [
    {"name": "Groq-Llama-3.3", "provider": "groq", "model": "llama-3.3-70b-versatile"},
    {"name": "Groq-Llama-3.1", "provider": "groq", "model": "llama-3.1-8b-instant"},
    {"name": "Groq-Gemma-2", "provider": "groq", "model": "gemma2-9b-it"},
    {"name": "OR-Llama-3.3-Free", "provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free"},
    {"name": "OR-Qwen-2.5-Free", "provider": "openrouter", "model": "qwen/qwen2.5-72b-instruct:free"},
    {"name": "OR-DeepSeek-Chat-Free", "provider": "openrouter", "model": "deepseek/deepseek-chat:free"},
    {"name": "HF-Qwen-2.5", "provider": "huggingface", "model": "Qwen/Qwen2.5-72B-Instruct"},
    {"name": "HF-Llama-3.3", "provider": "huggingface", "model": "meta-llama/Llama-3.3-70B-Instruct"},
    {"name": "HF-DeepSeek-V3", "provider": "huggingface", "model": "deepseek-ai/DeepSeek-V3"}
]

# ── Provider Configs ─────────────────────────────────────
PROVIDER_CONFIGS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key": GROK_API_KEY},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key": OPENROUTER_API_KEY},
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "api_key": HUGGINGFACE_API_KEY}
}



# ── English Coach Settings ───────────────────────────────
ENGLISH_COACH_VOICE = "en-US-JennyNeural"       # American female accent
ENGLISH_COACH_STT_LANG = "en-US"                 # Force English-only STT
ENGLISH_COACH_DATA = os.path.join(DATA_DIR, "english_coach_progress.json")
ENGLISH_COACH_SPEAKING_DURATION = 15             # seconds per user response
ENGLISH_COACH_PRONUNCIATION_WORDS = 8            # words per drill session

# ── Pronunciation Focus ──────────────────────────────────
# 6 high-impact pronunciation focus areas for learners
PRONUNCIATION_FOCUS = [
    {"area": "TH sound", "examples": ["think", "this", "through", "three", "method", "algorithm"]},
    {"area": "V vs W", "examples": ["very", "website", "version", "view", "variable", "workflow"]},
    {"area": "Ending consonants", "examples": ["worked", "tests", "projects", "fixed", "developed", "tasks"]},
    {"area": "R sound (rhotic)", "examples": ["server", "architecture", "performance", "render", "error", "parameter"]},
    {"area": "Sentence stress", "examples": ["I built a web application", "The server handles requests", "We deployed to production"]},
    {"area": "T-flap", "examples": ["better", "water", "letter", "data", "matter", "getting"]},
]

# ── UI Colors (Premium) ──────────────────────────
COLOR_PRIMARY = "#3b82f6"       # Bright Blue
COLOR_SECONDARY = "#10b981"     # Emerald Green
COLOR_ACCENT = "#8b5cf6"        # Violet
COLOR_WARNING = "#f59e0b"       # Amber
COLOR_DANGER = "#ef4444"        # Red
COLOR_BACKGROUND = "#111827"   # Gray-900 (Dark background)
COLOR_SURFACE = "#1f2937"      # Gray-800 (Card surface)
COLOR_TEXT_DIM = "#9ca3af"     # Gray-400 (Subheading)
COLOR_SUCCESS = "#059669"      # Emerald-600

