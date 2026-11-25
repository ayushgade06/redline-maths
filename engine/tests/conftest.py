import os
import sys
from pathlib import Path

# Tests are offline and deterministic unless RUN_LIVE=1. Setting the vars (even empty)
# stops load_dotenv() in main.py from pulling real credentials from .env.
if os.getenv("RUN_LIVE") != "1":
    os.environ["ANTHROPIC_API_KEY"] = ""
os.environ.setdefault("DATABASE_URL", "")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
