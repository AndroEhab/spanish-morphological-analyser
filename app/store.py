"""Backend dispatcher for the morphological analyser.

Selects the data backend at import time based on ``MORPH_BACKEND``:

- ``auto`` (default): use the SQLite store (``app/store_sqlite.py`` +
  ``data/morph.sqlite``) when both exist and import cleanly, else fall back
  to the fixture store (``app/store_fixture.py``).
- ``fixture``: always use the JSON fixture.
- ``sqlite``: always use the SQLite store; fails loudly if unavailable.

The three public functions (``search``, ``analyze``, ``health``) expose the
same shapes regardless of backend; ``backend_name`` reports which one is live.
"""

from __future__ import annotations

import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SQLITE_DB = _DATA_DIR / "morph.sqlite"


def _sqlite_ready() -> bool:
    if not _SQLITE_DB.exists():
        return False
    try:
        import app.store_sqlite  # noqa: F401 — real import, not just presence

        return True
    except Exception:
        return False


_mode = os.environ.get("MORPH_BACKEND", "auto").strip().lower()
if _mode not in ("auto", "fixture", "sqlite"):
    raise ValueError(f"MORPH_BACKEND must be one of auto|fixture|sqlite, got {_mode!r}")

if _mode == "sqlite":
    from app import store_sqlite as _impl  # noqa: F401 — fails loudly if missing

    _name = "sqlite"
elif _mode == "fixture":
    from app import store_fixture as _impl

    _name = "fixture"
elif _sqlite_ready():
    from app import store_sqlite as _impl

    _name = "sqlite"
else:
    from app import store_fixture as _impl

    _name = "fixture"


def search(q: str, limit: int) -> list[dict]:
    return _impl.search(q, limit)


def analyze(entry_id: str) -> dict | None:
    return _impl.analyze(entry_id)


def health() -> dict:
    body = dict(_impl.health())
    body["backend"] = _name
    return body


def backend_name() -> str:
    return _name
