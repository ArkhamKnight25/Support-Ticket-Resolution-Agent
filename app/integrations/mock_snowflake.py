import pandas as pd
from pathlib import Path
from app.services.logging_service import get_logger

logger = get_logger(__name__)

METRICS_FILE = Path("data/mock/service_metrics.csv")


def _load_df() -> pd.DataFrame:
    if not METRICS_FILE.exists():
        logger.warning("service_metrics.csv not found", path=str(METRICS_FILE))
        return pd.DataFrame()
    df = pd.read_csv(METRICS_FILE, parse_dates=["date"])
    return df


def _to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe dicts (converts Timestamps to strings)."""
    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = str(v.date()) if hasattr(v, "date") else v.isoformat()
    return records


def query_metrics(
    service: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    limit: int = 30,
) -> list[dict]:
    """Query service metrics like a SQL SELECT with filters."""
    df = _load_df()
    if df.empty:
        return []

    if service:
        df = df[df["service_name"] == service]
    if status:
        df = df[df["status"] == status]
    if date_from:
        df = df[df["date"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["date"] <= pd.to_datetime(date_to)]

    df = df.sort_values("date", ascending=False).head(limit)

    logger.info("metrics_query", service=service, rows=len(df))
    return _to_records(df)


def get_service_summary(service: str) -> dict:
    """Return aggregate stats for a service."""
    df = _load_df()
    if df.empty:
        return {}

    svc_df = df[df["service_name"] == service]
    if svc_df.empty:
        return {"service": service, "error": "No data found"}

    return {
        "service": service,
        "avg_error_rate": round(svc_df["error_rate"].mean(), 3),
        "avg_latency_ms": round(svc_df["latency_ms"].mean(), 1),
        "max_latency_ms": int(svc_df["latency_ms"].max()),
        "degraded_days": int((svc_df["status"] == "degraded").sum()),
        "total_days": len(svc_df),
        "latest_status": svc_df.sort_values("date").iloc[-1]["status"],
        "latest_date": str(svc_df["date"].max().date()),
    }


def get_degraded_events(service: str | None = None) -> list[dict]:
    """Return all days where any service (or a specific one) was degraded."""
    df = _load_df()
    degraded = df[df["status"] == "degraded"]
    if service:
        degraded = degraded[degraded["service_name"] == service]
    return _to_records(degraded.sort_values("date", ascending=False))
