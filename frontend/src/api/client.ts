export type HealthResponse = {
    status: string;
};

export type ScenarioRow = {
    center_id: string;
    center_name: string;
    shipping_cost: number;
    baseline_order_count: number;
    staffing_level: number;
    fixed_cost: number;
};

export type DashboardMetrics = {
    total_cost: number;
    total_orders: number;
    avg_unit_cost: number;
    unassigned_order_count: number;
    total_labor_cost: number;
    total_fixed_cost: number;
};

export type CenterSummaryRow = {
    center_name: string;
    shipping_cost: number;
    assigned_orders: number;
    staffing_level: number;
    capacity: number;
    fixed_cost: number;
    labor_cost: number;
    variable_cost: number;
    total_cost: number;
};

export type DashboardResponse = {
    scenario_rows: ScenarioRow[];
    center_summary_rows: CenterSummaryRow[];
    metrics: DashboardMetrics;
};

export async function fetchHealth(): Promise<HealthResponse> {
    const response = await fetch("/api/health");

    if (!response.ok) {
        throw new Error(`health request failed: ${response.status}`);
    }

    return (await response.json()) as HealthResponse;
}


export async function fetchDashboardBootstrap(): Promise<DashboardResponse> {
    const response = await fetch("/api/dashboard/bootstrap");

    if (!response.ok) {
        throw new Error(`dashboard bootstrap failed: ${response.status}`);
    }

    return (await response.json()) as DashboardResponse;
}


export async function simulateDashboard(scenarioRows: ScenarioRow[]): Promise<DashboardResponse> {
    const response = await fetch("/api/dashboard/simulate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ scenario_rows: scenarioRows }),
    });

    if (!response.ok) {
        throw new Error(`dashboard simulate failed: ${response.status}`);
    }

    return (await response.json()) as DashboardResponse;
}