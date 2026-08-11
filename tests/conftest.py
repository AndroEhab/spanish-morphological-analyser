"""Hermetic test configuration.

Force the fixture backend before anything imports ``app``, so the suite
passes identically whether or not the pipeline's SQLite artifacts
(``app/store_sqlite.py``, ``data/morph.sqlite``) exist yet. Setting
``MORPH_BACKEND=sqlite`` explicitly opts the API tests into the real
SQLite backend.
"""

import os

os.environ.setdefault("MORPH_BACKEND", "fixture")
