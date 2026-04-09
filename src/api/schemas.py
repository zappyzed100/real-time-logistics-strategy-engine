from pydantic import BaseModel


class ScenarioRow(BaseModel):
    center_id: str
    center_name: str
    shipping_cost: float
    baseline_order_count: int
    staffing_level: int
    fixed_cost: float


class DashboardMetrics(BaseModel):
    total_cost: float
    total_orders: int
    avg_unit_cost: float
    unassigned_order_count: int
    total_labor_cost: float
    total_fixed_cost: float


class CenterSummaryRow(BaseModel):
    center_name: str
    shipping_cost: float
    assigned_orders: int
    staffing_level: int
    capacity: int
    fixed_cost: float
    labor_cost: float
    variable_cost: float
    total_cost: float


class OrderRow(BaseModel):
    order_id: str
    assigned_center_name: str
    assignment_status: str
    fallback_center_name: str
    simulated_cost: float
    simulated_distance_km: float
    weight_kg: float


class DashboardResponse(BaseModel):
    scenario_rows: list[ScenarioRow]
    center_summary_rows: list[CenterSummaryRow]
    order_rows: list[OrderRow]
    metrics: DashboardMetrics


class SimulationRequest(BaseModel):
    scenario_rows: list[ScenarioRow]
