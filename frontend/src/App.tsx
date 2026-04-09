import { useEffect, useRef, useState } from "react";
import {
    fetchDashboardBootstrap,
    fetchHealth,
    simulateDashboard,
    type DashboardResponse,
    type OrderRow,
    type ScenarioRow,
} from "./api/client";
import { SimulationMap } from "./components/SimulationMap";

type DisplayMode = "dashboard" | "orders";
type OrderSortKey = "simulated_cost" | "simulated_distance_km" | "weight_kg" | "order_id";
const ORDER_PAGE_SIZE = 100;

function App() {
    const [healthStatus, setHealthStatus] = useState<string>("loading");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null);
    const [scenarioRows, setScenarioRows] = useState<ScenarioRow[]>([]);
    const [isSimulating, setIsSimulating] = useState<boolean>(false);
    const [displayMode, setDisplayMode] = useState<DisplayMode>("dashboard");
    const [orderSearchText, setOrderSearchText] = useState<string>("");
    const [orderStatusFilter, setOrderStatusFilter] = useState<"all" | "割当済" | "未割当">("all");
    const [orderSortKey, setOrderSortKey] = useState<OrderSortKey>("simulated_cost");
    const [orderCenterFilter, setOrderCenterFilter] = useState<string>("all");
    const [orderPage, setOrderPage] = useState<number>(1);
    const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
    const hasBootstrappedRef = useRef<boolean>(false);
    const lastSimulatedSignatureRef = useRef<string>("");
    const mapSectionRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        let isMounted = true;

        Promise.all([fetchHealth(), fetchDashboardBootstrap()])
            .then(([healthPayload, dashboardPayload]) => {
                if (!isMounted) {
                    return;
                }
                setHealthStatus(healthPayload.status);
                setDashboardData(dashboardPayload);
                setScenarioRows(dashboardPayload.scenario_rows);
                lastSimulatedSignatureRef.current = getScenarioSignature(dashboardPayload.scenario_rows);
                hasBootstrappedRef.current = true;
            })
            .catch((error: unknown) => {
                if (!isMounted) {
                    return;
                }
                setErrorMessage(error instanceof Error ? error.message : "unknown error");
                setHealthStatus("error");
            });

        return () => {
            isMounted = false;
        };
    }, []);

    async function handleSimulate(nextScenarioRows: ScenarioRow[]) {
        try {
            setIsSimulating(true);
            setErrorMessage(null);
            const nextDashboardData = await simulateDashboard(nextScenarioRows);
            lastSimulatedSignatureRef.current = getScenarioSignature(nextDashboardData.scenario_rows);
            setDashboardData(nextDashboardData);
            setScenarioRows(nextDashboardData.scenario_rows);
        } catch (error: unknown) {
            setErrorMessage(error instanceof Error ? error.message : "unknown error");
        } finally {
            setIsSimulating(false);
        }
    }

    function handleScenarioNumberChange(centerId: string, field: "staffing_level" | "fixed_cost", value: string) {
        const numericValue = Number(value);
        const nextValue = Number.isFinite(numericValue) && numericValue >= 0 ? numericValue : 0;

        setScenarioRows((currentRows) =>
            currentRows.map((row) => {
                if (row.center_id !== centerId) {
                    return row;
                }

                return {
                    ...row,
                    [field]: field === "staffing_level" ? Math.round(nextValue) : nextValue,
                };
            }),
        );
    }

    useEffect(() => {
        if (!hasBootstrappedRef.current) {
            return;
        }

        const nextSignature = getScenarioSignature(scenarioRows);
        if (nextSignature === lastSimulatedSignatureRef.current) {
            return;
        }

        const timeoutId = window.setTimeout(() => {
            void handleSimulate(scenarioRows);
        }, 250);

        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [scenarioRows]);

    useEffect(() => {
        setOrderPage(1);
    }, [orderSearchText, orderStatusFilter, orderSortKey, orderCenterFilter]);

    useEffect(() => {
        if (displayMode !== "dashboard" || !selectedOrderId) {
            return;
        }

        mapSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, [displayMode, selectedOrderId]);

    const filteredOrderRows = dashboardData
        ? getFilteredOrderRows(dashboardData.order_rows, {
            searchText: orderSearchText,
            statusFilter: orderStatusFilter,
            sortKey: orderSortKey,
            centerFilter: orderCenterFilter,
        })
        : [];
    const orderPageCount = Math.max(1, Math.ceil(filteredOrderRows.length / ORDER_PAGE_SIZE));
    const currentOrderPage = Math.min(orderPage, orderPageCount);
    const paginatedOrderRows = filteredOrderRows.slice(
        (currentOrderPage - 1) * ORDER_PAGE_SIZE,
        currentOrderPage * ORDER_PAGE_SIZE,
    );
    const orderCenterOptions = dashboardData ? getOrderCenterOptions(dashboardData.order_rows) : [];
    const selectedMapOrder = dashboardData?.map_order_rows.find((row) => row.order_id === selectedOrderId) ?? null;

    return (
        <main className="app-shell">
            <section className={`hero-card ${displayMode === "dashboard" ? "is-dashboard" : "is-wide"}`}>
                <h1>FastAPI + React migration</h1>
                <p className="lead">
                    Streamlit から差分更新型 UI へ移行するためのフロントエンド基盤です。まずは FastAPI との接続と
                    開発基盤を立ち上げています。
                </p>
                <div className="status-row">
                    <span className="status-label">API health</span>
                    <span className={`status-pill status-${healthStatus}`}>{healthStatus}</span>
                </div>
                {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
                {dashboardData ? (
                    <>
                        <section className="mode-switch" aria-label="表示モード">
                            <button
                                type="button"
                                className={`mode-button ${displayMode === "dashboard" ? "is-active" : ""}`}
                                onClick={() => setDisplayMode("dashboard")}
                            >
                                ダッシュボード
                            </button>
                            <button
                                type="button"
                                className={`mode-button ${displayMode === "orders" ? "is-active" : ""}`}
                                onClick={() => setDisplayMode("orders")}
                            >
                                注文別データ一覧
                            </button>
                        </section>

                        {displayMode === "dashboard" ? (
                            <div className="dashboard-layout">
                                <aside className="scenario-sidebar-card">
                                    <div className="scenario-sidebar-header">
                                        <div>
                                            <h2>拠点情報</h2>
                                            <p>変更は自動で反映されます。</p>
                                        </div>
                                        <span className={`sync-chip ${isSimulating ? "is-active" : ""}`}>{isSimulating ? "反映中..." : "同期済み"}</span>
                                    </div>
                                    <div className="scenario-sidebar-grid">
                                        {scenarioRows.map((row) => (
                                            <article key={row.center_id} className="scenario-sidebar-row is-inline">
                                                <strong>{row.center_name}</strong>
                                                <input
                                                    className="table-input"
                                                    type="number"
                                                    min="0"
                                                    step="1"
                                                    value={row.staffing_level}
                                                    onChange={(event) =>
                                                        handleScenarioNumberChange(row.center_id, "staffing_level", event.target.value)
                                                    }
                                                />
                                                <input
                                                    className="table-input"
                                                    type="number"
                                                    min="0"
                                                    step="1000000"
                                                    value={row.fixed_cost}
                                                    onChange={(event) =>
                                                        handleScenarioNumberChange(row.center_id, "fixed_cost", event.target.value)
                                                    }
                                                />
                                            </article>
                                        ))}
                                    </div>
                                </aside>

                                <div className="dashboard-main">
                                    <section className="metrics-grid metrics-grid-overview">
                                        <article className="metric-card">
                                            <span className="metric-label">対象拠点数</span>
                                            <strong>{formatInteger(scenarioRows.length)} 拠点</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">設定人員合計</span>
                                            <strong>{formatInteger(sumScenarioValues(scenarioRows, "staffing_level"))} 人</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">固定費合計</span>
                                            <strong>{formatCurrency(sumScenarioValues(scenarioRows, "fixed_cost"))}</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">人件費合計</span>
                                            <strong>{formatCurrency(dashboardData.metrics.total_labor_cost)}</strong>
                                        </article>
                                    </section>

                                    <section className="data-section">
                                        <div className="section-heading">
                                            <h2>Key Performance Indicators</h2>
                                            <span>シミュレーション結果</span>
                                        </div>
                                    </section>

                                    <section className="metrics-grid">
                                        <article className="metric-card">
                                            <span className="metric-label">総コスト</span>
                                            <strong>{formatCurrency(dashboardData.metrics.total_cost)}</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">総注文数</span>
                                            <strong>{formatInteger(dashboardData.metrics.total_orders)} 件</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">平均配送単価</span>
                                            <strong>{formatCurrency(dashboardData.metrics.avg_unit_cost)}</strong>
                                        </article>
                                        <article className="metric-card">
                                            <span className="metric-label">未割当注文</span>
                                            <strong>{formatInteger(dashboardData.metrics.unassigned_order_count)} 件</strong>
                                        </article>
                                    </section>

                                    <section className="data-section">
                                        <div className="section-heading">
                                            <h2>分析詳細</h2>
                                            <span>拠点別総コスト</span>
                                        </div>
                                        <div className="chart-scroll-shell">
                                            <div
                                                className="vertical-bar-chart"
                                                style={{ width: `${Math.max(dashboardData.center_summary_rows.length * 44, 960)}px` }}
                                            >
                                                {dashboardData.center_summary_rows.map((row) => (
                                                    <div key={row.center_name} className="vertical-bar-item">
                                                        <div className="vertical-bar-value">{formatShortCurrency(row.total_cost)}</div>
                                                        <div className="vertical-bar-track">
                                                            <div
                                                                className="vertical-bar-fill"
                                                                style={{ height: `${getCostBarWidth(row.total_cost, dashboardData.center_summary_rows)}%` }}
                                                            />
                                                        </div>
                                                        <div className="vertical-bar-label">{row.center_name}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </section>

                                    <section className="data-section" ref={mapSectionRef}>
                                        <div className="section-heading">
                                            <h2>地図</h2>
                                            <span>{formatInteger(dashboardData.map_order_rows.length)} 件を表示</span>
                                        </div>
                                        <p className="map-caption">
                                            OpenStreetMap 上に注文データを最大 10,000 件表示します。未割当は赤、低コストは青、高コストは黄です。
                                        </p>
                                        <div className="map-layout is-embedded">
                                            <SimulationMap
                                                orderRows={dashboardData.map_order_rows}
                                                centerRows={dashboardData.map_center_rows}
                                                selectedOrderId={selectedOrderId}
                                                selectedOrder={selectedMapOrder}
                                            />
                                            <aside className="map-legend">
                                                <h3>凡例</h3>
                                                <p><span className="legend-dot is-low-cost" /> 低コスト注文</p>
                                                <p><span className="legend-dot is-high-cost" /> 高コスト注文</p>
                                                <p><span className="legend-dot is-unassigned" /> 未割当注文</p>
                                                <p><span className="legend-dot is-center" /> 物流拠点</p>
                                                <div className="map-legend-metrics">
                                                    <span>表示注文数</span>
                                                    <strong>{formatInteger(dashboardData.map_order_rows.length)} 件</strong>
                                                    <span>表示拠点数</span>
                                                    <strong>{formatInteger(dashboardData.map_center_rows.length)} 拠点</strong>
                                                </div>
                                            </aside>
                                        </div>
                                    </section>

                                    <section className="data-section">
                                        <div className="section-heading">
                                            <h2>拠点別コスト集計</h2>
                                            <span>分析詳細</span>
                                        </div>
                                        <div className="table-shell">
                                            <table>
                                                <thead>
                                                    <tr>
                                                        <th>拠点</th>
                                                        <th>基準注文数</th>
                                                        <th>配送係数</th>
                                                        <th>担当注文数</th>
                                                        <th>人員数</th>
                                                        <th>処理可能件数</th>
                                                        <th>固定費</th>
                                                        <th>人件費</th>
                                                        <th>配送費</th>
                                                        <th>総コスト</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {dashboardData.center_summary_rows.map((row) => (
                                                        <tr key={row.center_name}>
                                                            <td>{row.center_name}</td>
                                                            <td>{formatInteger(getScenarioRowByCenterName(scenarioRows, row.center_name)?.baseline_order_count ?? 0)}</td>
                                                            <td>{row.shipping_cost.toFixed(3)}</td>
                                                            <td>{formatInteger(row.assigned_orders)}</td>
                                                            <td>{formatInteger(row.staffing_level)}</td>
                                                            <td>{formatInteger(row.capacity)}</td>
                                                            <td>{formatCurrency(row.fixed_cost)}</td>
                                                            <td>{formatCurrency(row.labor_cost)}</td>
                                                            <td>{formatCurrency(row.variable_cost)}</td>
                                                            <td>{formatCurrency(row.total_cost)}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </section>
                                </div>
                            </div>
                        ) : (
                            <section className="data-section">
                                <div className="section-heading">
                                    <h2>注文別データ一覧</h2>
                                    <span>{formatInteger(filteredOrderRows.length)} 件 / {formatInteger(currentOrderPage)} ページ</span>
                                </div>
                                <div className="table-toolbar">
                                    <label className="toolbar-field search-field">
                                        <span>検索</span>
                                        <input
                                            className="table-input"
                                            type="search"
                                            value={orderSearchText}
                                            placeholder="注文ID / 担当拠点"
                                            onChange={(event) => setOrderSearchText(event.target.value)}
                                        />
                                    </label>
                                    <label className="toolbar-field">
                                        <span>割当状態</span>
                                        <select
                                            className="table-select"
                                            value={orderStatusFilter}
                                            onChange={(event) =>
                                                setOrderStatusFilter(event.target.value as "all" | "割当済" | "未割当")
                                            }
                                        >
                                            <option value="all">すべて</option>
                                            <option value="割当済">割当済</option>
                                            <option value="未割当">未割当</option>
                                        </select>
                                    </label>
                                    <label className="toolbar-field">
                                        <span>担当拠点</span>
                                        <select
                                            className="table-select"
                                            value={orderCenterFilter}
                                            onChange={(event) => setOrderCenterFilter(event.target.value)}
                                        >
                                            <option value="all">すべて</option>
                                            {orderCenterOptions.map((centerName) => (
                                                <option key={centerName} value={centerName}>{centerName}</option>
                                            ))}
                                        </select>
                                    </label>
                                    <label className="toolbar-field">
                                        <span>並び順</span>
                                        <select
                                            className="table-select"
                                            value={orderSortKey}
                                            onChange={(event) => setOrderSortKey(event.target.value as OrderSortKey)}
                                        >
                                            <option value="simulated_cost">配送コスト順</option>
                                            <option value="simulated_distance_km">距離順</option>
                                            <option value="weight_kg">重量順</option>
                                            <option value="order_id">注文ID順</option>
                                        </select>
                                    </label>
                                </div>
                                <div className="table-shell order-table-shell">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>注文ID</th>
                                                <th>担当拠点</th>
                                                <th>割当状態</th>
                                                <th>代替拠点</th>
                                                <th>配送コスト</th>
                                                <th>距離</th>
                                                <th>重量</th>
                                                <th>地図</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {paginatedOrderRows.map((row) => (
                                                <tr key={row.order_id}>
                                                    <td>{row.order_id}</td>
                                                    <td>{row.assigned_center_name}</td>
                                                    <td>
                                                        <AssignmentStatusBadge row={row} />
                                                    </td>
                                                    <td>{row.fallback_center_name || "-"}</td>
                                                    <td>{formatCurrency(row.simulated_cost)}</td>
                                                    <td>{formatDistance(row.simulated_distance_km)}</td>
                                                    <td>{formatWeight(row.weight_kg)}</td>
                                                    <td>
                                                        <button
                                                            type="button"
                                                            className="link-button"
                                                            onClick={() => {
                                                                setSelectedOrderId(row.order_id);
                                                                setDisplayMode("dashboard");
                                                            }}
                                                        >
                                                            地図で見る
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                <div className="pagination-row">
                                    <button
                                        type="button"
                                        className="secondary-button"
                                        onClick={() => setOrderPage((current) => Math.max(1, current - 1))}
                                        disabled={currentOrderPage <= 1}
                                    >
                                        前へ
                                    </button>
                                    <span>{formatInteger(currentOrderPage)} / {formatInteger(orderPageCount)}</span>
                                    <button
                                        type="button"
                                        className="secondary-button"
                                        onClick={() => setOrderPage((current) => Math.min(orderPageCount, current + 1))}
                                        disabled={currentOrderPage >= orderPageCount}
                                    >
                                        次へ
                                    </button>
                                </div>
                            </section>
                        )}
                    </>
                ) : null}
            </section>
        </main>
    );
}

function AssignmentStatusBadge({ row }: { row: OrderRow }) {
    const className = row.assignment_status === "未割当" ? "status-badge is-warning" : "status-badge is-ok";

    return <span className={className}>{row.assignment_status}</span>;
}

function formatCurrency(value: number): string {
    return new Intl.NumberFormat("ja-JP", {
        style: "currency",
        currency: "JPY",
        maximumFractionDigits: 0,
    }).format(value);
}

function formatInteger(value: number): string {
    return new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 0 }).format(value);
}

function formatDistance(value: number): string {
    return `${new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 }).format(value)} km`;
}

function formatWeight(value: number): string {
    return `${new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 }).format(value)} kg`;
}

function sumScenarioValues(rows: ScenarioRow[], field: "staffing_level" | "fixed_cost"): number {
    return rows.reduce((total, row) => total + row[field], 0);
}

function getCostBarWidth(totalCost: number, rows: DashboardResponse["center_summary_rows"]): number {
    const maxCost = rows.reduce((currentMax, row) => Math.max(currentMax, row.total_cost), 0);
    if (maxCost <= 0) {
        return 0;
    }

    return (totalCost / maxCost) * 100;
}

function formatShortCurrency(value: number): string {
    if (value >= 100_000_000) {
        return `${(value / 100_000_000).toFixed(1)}億円`;
    }

    return `${Math.round(value / 10_000).toLocaleString("ja-JP")}万円`;
}

function getScenarioSignature(rows: ScenarioRow[]): string {
    return JSON.stringify(rows.map((row) => [row.center_id, row.staffing_level, row.fixed_cost]));
}

function getScenarioRowByCenterName(rows: ScenarioRow[], centerName: string): ScenarioRow | undefined {
    return rows.find((row) => row.center_name === centerName);
}

function getFilteredOrderRows(
    rows: OrderRow[],
    options: {
        searchText: string;
        statusFilter: "all" | "割当済" | "未割当";
        sortKey: OrderSortKey;
        centerFilter: string;
    },
): OrderRow[] {
    const normalizedSearchText = options.searchText.trim().toLowerCase();
    const filteredRows = rows.filter((row) => {
        const matchesStatus = options.statusFilter === "all" || row.assignment_status === options.statusFilter;
        const matchesCenter = options.centerFilter === "all" || row.assigned_center_name === options.centerFilter;
        if (!matchesStatus || !matchesCenter) {
            return false;
        }

        if (!normalizedSearchText) {
            return true;
        }

        return [row.order_id, row.assigned_center_name, row.fallback_center_name]
            .join(" ")
            .toLowerCase()
            .includes(normalizedSearchText);
    });

    return [...filteredRows].sort((left, right) => {
        if (options.sortKey === "order_id") {
            return left.order_id.localeCompare(right.order_id, "ja");
        }

        return right[options.sortKey] - left[options.sortKey];
    });
}

function getOrderCenterOptions(rows: OrderRow[]): string[] {
    return [...new Set(rows.map((row) => row.assigned_center_name).filter((centerName) => centerName !== ""))].sort((left, right) =>
        left.localeCompare(right, "ja"),
    );
}

export default App;