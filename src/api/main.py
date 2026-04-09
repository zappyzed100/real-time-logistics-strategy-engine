from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dashboard_service import get_dashboard_bootstrap, simulate_dashboard
from src.api.schemas import DashboardResponse, SimulationRequest

app = FastAPI(title="real-time-logistics-strategy-engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "real-time-logistics-strategy-engine-api", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard/bootstrap", response_model=DashboardResponse)
def dashboard_bootstrap() -> DashboardResponse:
    return get_dashboard_bootstrap()


@app.post("/dashboard/simulate", response_model=DashboardResponse)
def dashboard_simulate(request: SimulationRequest) -> DashboardResponse:
    return simulate_dashboard(request.scenario_rows, include_order_rows=request.include_order_rows)
