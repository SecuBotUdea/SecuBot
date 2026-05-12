"""
Mock del normalizador externo para pruebas locales.

Controla el escenario via variable de entorno o endpoint:
  MOCK_SCENARIO=resolved   → reopen_count igual al local (vulnerabilidad resuelta)
  MOCK_SCENARIO=persists   → reopen_count mayor al local (vulnerabilidad persiste)

Endpoints:
  GET  /                          → health check
  GET  /alerts/{alert_id}         → respuesta simulada del normalizador
  POST /scenario/{name}           → cambia el escenario en caliente (resolved | persists)

Uso:
  python scripts/mock_normalizer.py
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Normalizer")

# Estado global del mock
state = {"scenario": os.getenv("MOCK_SCENARIO", "resolved")}

SCENARIOS = {
    # reopen_count == 0 → igual al local (0) → still_exists = False → RESUELTA
    "resolved": {"reopen_count": 0},
    # reopen_count == 1 → mayor al local (0) → still_exists = True → PERSISTE
    "persists": {"reopen_count": 1},
}


@app.get("/")
def health():
    return {"status": "ok", "mock": True, "scenario": state["scenario"]}


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    scenario = state["scenario"]
    data = SCENARIOS.get(scenario, SCENARIOS["resolved"])
    print(f"[mock] GET /alerts/{alert_id}  scenario={scenario}  → {data}")
    return JSONResponse(content={"alert_id": alert_id, **data})


@app.post("/scenario/{name}")
def set_scenario(name: str):
    if name not in SCENARIOS:
        return JSONResponse(status_code=400, content={"error": f"Escenario desconocido: {name}. Usa: {list(SCENARIOS)}"})
    state["scenario"] = name
    print(f"[mock] Escenario cambiado a: {name}")
    return {"scenario": name, "response": SCENARIOS[name]}


if __name__ == "__main__":
    port = int(os.getenv("MOCK_PORT", "8001"))
    print(f"Mock normalizer arrancando en http://localhost:{port}")
    print(f"Escenario inicial: {state['scenario']}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
