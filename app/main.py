"""Spanish Morphological Analyser — FastAPI application.

Serves the static frontend from ``app/static`` at ``/`` and the JSON API
under ``/api``. Dict return types are serialized natively by FastAPI
(orjson remains in requirements for the upcoming SQLite pipeline).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Spanish Morphological Analyser")

app.include_router(router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
