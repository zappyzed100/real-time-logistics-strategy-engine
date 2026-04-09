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

export type OrderRow = {
    order_id: string;
    prefecture: string;
    assigned_center_name: string;
    assignment_status: string;
    fallback_center_name: string;
    simulated_cost: number;
    simulated_distance_km: number;
    weight_kg: number;
};

export type MapOrderRow = {
    order_id: string;
    customer_lat: number;
    customer_lon: number;
    assigned_center_name: string;
    assignment_status: string;
    simulated_cost: number;
    weight_kg: number;
    is_unassigned: boolean;
    color_r: number;
    color_g: number;
    color_b: number;
};

export type MapCenterRow = {
    center_id: string;
    center_name: string;
    center_lat: number;
    center_lon: number;
    staffing_level: number;
    fixed_cost: number;
};

export type DashboardResponse = {
    scenario_rows: ScenarioRow[];
    center_summary_rows: CenterSummaryRow[];
    order_rows: OrderRow[];
    map_order_rows: MapOrderRow[];
    map_center_rows: MapCenterRow[];
    metrics: DashboardMetrics;
};

const API_CONFIGURATION = resolveApiConfiguration();

function resolveApiConfiguration(): { baseUrl: string; pathPrefix: string } {
    const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
    if (configuredBaseUrl) {
        return {
            baseUrl: configuredBaseUrl.replace(/\/$/, ""),
            pathPrefix: "",
        };
    }

    if (typeof window === "undefined") {
        return { baseUrl: "", pathPrefix: "/api" };
    }

    const { hostname, port, protocol } = window.location;
    const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";
    if (isLocalhost && port !== "8000") {
        return {
            baseUrl: `${protocol}//${hostname}:8000`,
            pathPrefix: "",
        };
    }

    return { baseUrl: "", pathPrefix: "/api" };
}

function buildApiUrl(path: string): string {
    return `${API_CONFIGURATION.baseUrl}${API_CONFIGURATION.pathPrefix}${path}`;
}

async function readJsonResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
    if (contentType.includes("application/json")) {
        return (await response.json()) as T;
    }

    const responseText = await response.text();
    const snippet = responseText.slice(0, 120).replace(/\s+/g, " ").trim();
    throw new Error(`API returned non-JSON response: ${snippet || response.status}`);
}

export async function fetchHealth(): Promise<HealthResponse> {
    const response = await fetch(buildApiUrl("/health"));

    if (!response.ok) {
        throw new Error(`health request failed: ${response.status}`);
    }

    return await readJsonResponse<HealthResponse>(response);
}


export async function fetchDashboardBootstrap(): Promise<DashboardResponse> {
    const response = await fetch(buildApiUrl("/dashboard/bootstrap"));

    if (!response.ok) {
        throw new Error(`dashboard bootstrap failed: ${response.status}`);
    }

    return await readJsonResponse<DashboardResponse>(response);
}


export async function simulateDashboard(
    scenarioRows: ScenarioRow[],
    options?: { signal?: AbortSignal; includeOrderRows?: boolean; includeMapRows?: boolean },
): Promise<DashboardResponse> {
    const response = await fetch(buildApiUrl("/dashboard/simulate"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        signal: options?.signal,
        body: JSON.stringify({
            scenario_rows: scenarioRows,
            include_order_rows: options?.includeOrderRows ?? true,
            include_map_rows: options?.includeMapRows ?? true,
        }),
    });

    if (!response.ok) {
        throw new Error(`dashboard simulate failed: ${response.status}`);
    }

    return await readJsonResponse<DashboardResponse>(response);
}