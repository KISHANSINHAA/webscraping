import os

# Manual .env parser to load configuration dynamically without dependencies
def _load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

_load_env_file()

# ========= CONFIG =========
# Groq API Key extracted safely from local environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq endpoint configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model choice extracted safely from local environment
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Scraping & Discovery Settings
TIMEOUT = 10
MAX_DISCOVERED_PAGES = 5

PRIORITY_KEYWORDS = [
    "about",
    "about-us",
    "company",
    "services",
    "solutions",
    "products",
    "contact",
    "contact-us",
    "who-we-are",
    "industries"
]

IGNORE_KEYWORDS = [
    "blog",
    "careers",
    "privacy",
    "terms",
    "news",
    "events"
]

# Database Config
DB_NAME = "prospects.db"
