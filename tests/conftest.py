"""
conftest.py – Configuración global de pytest para SecuBot.

IMPORTANT: os.environ must be set BEFORE any app module is imported,
because config/settings.py creates the Settings() singleton at import time
and requires MONGODB_URI to be present.
"""

import os

# ─── Required env vars ───────────────────────────────────────────────────────
# Set a dummy MongoDB URI so Settings() can be instantiated during import.
# Tests that actually need DB access must mock get_database() themselves.
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "secubot_test")
os.environ.setdefault("ENVIRONMENT", "test")

# ─── pytest-asyncio mode ─────────────────────────────────────────────────────
# Already set to "auto" in pytest.ini; no fixture needed.
