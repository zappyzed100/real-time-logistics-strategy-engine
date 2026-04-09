import { useEffect, useState } from "react";
import { fetchHealth } from "./api/client";

function App() {
    const [healthStatus, setHealthStatus] = useState<string>("loading");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        fetchHealth()
            .then((payload) => {
                if (!isMounted) {
                    return;
                }
                setHealthStatus(payload.status);
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
            </section>
        </main>
    );
}

export default App;