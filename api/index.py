"""Vercel entry point: the FastAPI engine runs as one Python function behind /api/*."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from main import app  # noqa: E402,F401
