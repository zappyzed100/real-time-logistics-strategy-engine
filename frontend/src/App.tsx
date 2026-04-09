import { useEffect, useState } from "react";
import {
    fetchDashboardBootstrap,
    fetchHealth,
    simulateDashboard,
    type DashboardResponse,
    type OrderRow,
    type ScenarioRow,
} from "./api/client";
import { SimulationMap } from "./components/SimulationMap";

type DisplayMode = "dashboard" | "orders" | "map";

function App() {
    const [healthStatus, setHealthStatus] = useState<string>("loading");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null);
    const [scenarioRows, setScenarioRows] = useState<ScenarioRow[]>([]);
    const [isSimulating, setIsSimulating] = useState<boolean>(false);
    const [displayMode, setDisplayMode] = useState<DisplayMode>("dashboard");

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

    async function handleSimulate() {
        try {
            setIsSimulating(true);
            setErrorMessage(null);
            const nextDashboardData = await simulateDashboard(scenarioRows);
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

    return (
        <main className="app-shell">
            <section className={`hero-card ${displayMode === "dashboard" ? "is-dashboard" : "is-wide"}`}>
                <p className="eyebrow">Issue #223</p>
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
                            <button
                                type="button"
                                className={`mode-button ${displayMode === "map" ? "is-active" : ""}`}
                                onClick={() => setDisplayMode("map")}
                            >
                                地図
                            </button>
                        </section>

                        {displayMode === "dashboard" ? (
                            <div className="dashboard-layout">
                                <aside className="scenario-sidebar-card">
                                    <div className="scenario-sidebar-header">
                                        <div>
                                            <h2>拠点情報</h2>
                                            <p>固定費は 100 万円単位です。</p>
                                        </div>
                                        <button type="button" className="primary-button" onClick={handleSimulate} disabled={isSimulating}>
                                            {isSimulating ? "再計算中..." : "再計算"}
                                        </button>
                                    </div>
                                    <div className="scenario-sidebar-grid">
                                        {scenarioRows.map((row) => (
                                            <article key={row.center_id} className="scenario-sidebar-row">
                                                <div className="scenario-sidebar-title-row">
                                                    <strong>{row.center_name}</strong>
                                                    <span>{row.shipping_cost.toFixed(3)}</span>
                                                </div>
                                                <span className="scenario-sidebar-subtext">基準注文数 {formatInteger(row.baseline_order_count)} 件</span>
                                                <div className="scenario-sidebar-inputs">
                                                    <label>
                                                        <span>人員数</span>
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
                                                    </label>
                                                    <label>
                                                        <span>固定費</span>
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
                                                    </label>
                                                </div>
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
                                        <div className="cost-bar-list">
                                            {dashboardData.center_summary_rows.map((row) => (
                                                <div key={row.center_name} className="cost-bar-row">
                                                    <div className="cost-bar-header">
                                                        <strong>{row.center_name}</strong>
                                                        <span>{formatCurrency(row.total_cost)}</span>
                                                    </div>
                                                    <div className="cost-bar-track">
                                                        <div
                                                            className="cost-bar-fill"
                                                            style={{ width: `${getCostBarWidth(row.total_cost, dashboardData.center_summary_rows)}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ))}
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
                        ) : displayMode === "orders" ? (
                            <section className="data-section">
                                <div className="section-heading">
                                    <h2>注文別データ一覧</h2>
                                    <span>{formatInteger(dashboardData.order_rows.length)} 件</span>
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
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {dashboardData.order_rows.map((row) => (
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
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        ) : (
                            <section className="data-section">
                                <div className="section-heading">
                                    <h2>配送エリア・コスト分布の地理的分析</h2>
                                    <span>{formatInteger(dashboardData.map_order_rows.length)} 件を表示</span>
                                </div>
                                <p className="map-caption">
                                    OpenStreetMap 上に注文データを最大 10,000 件表示します。未割当は赤、低コストは青、高コストは黄です。
                                </p>
                                <div className="map-layout">
                                    <SimulationMap orderRows={dashboardData.map_order_rows} centerRows={dashboardData.map_center_rows} />
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

export default App;