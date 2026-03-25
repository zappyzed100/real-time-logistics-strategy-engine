from fastapi import FastAPI

app = FastAPI(title="real-time-logistics-strategy-engine API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
