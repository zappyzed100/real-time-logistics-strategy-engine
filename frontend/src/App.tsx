import { useEffect, useState } from "react";
import { fetchDashboardBootstrap, fetchHealth, type DashboardResponse } from "./api/client";

function App() {
    const [healthStatus, setHealthStatus] = useState<string>("loading");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null);

    useEffect(() => {
        let isMounted = true;

        Promise.all([fetchHealth(), fetchDashboardBootstrap()])
            .then(([healthPayload, dashboardPayload]) => {
                if (!isMounted) {
                    return;
                }
                setHealthStatus(healthPayload.status);
                setDashboardData(dashboardPayload);
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

    return (
        <main className="app-shell">
            <section className="hero-card">
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
                                <h2>拠点シナリオ</h2>
                                <span>{formatInteger(dashboardData.scenario_rows.length)} 拠点</span>
                            </div>
                            <div className="table-shell">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>拠点</th>
                                            <th>配送係数</th>
                                            <th>基準注文数</th>
                                            <th>人員数</th>
                                            <th>固定費</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {dashboardData.scenario_rows.map((row) => (
                                            <tr key={row.center_id}>
                                                <td>{row.center_name}</td>
                                                <td>{row.shipping_cost.toFixed(3)}</td>
                                                <td>{formatInteger(row.baseline_order_count)}</td>
                                                <td>{formatInteger(row.staffing_level)}</td>
                                                <td>{formatCurrency(row.fixed_cost)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section className="data-section">
                            <div className="section-heading">
                                <h2>拠点別コスト集計</h2>
                                <span>初期表示</span>
                            </div>
                            <div className="table-shell">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>拠点</th>
                                            <th>配送係数</th>
                                            <th>担当注文数</th>
                                            <th>人員数</th>
                                            <th>固定費</th>
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
                                                <td>{formatCurrency(row.fixed_cost)}</td>
                                                <td>{formatCurrency(row.total_cost)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </>
                ) : null}
            </section>
        </main>
    );
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

export default App;