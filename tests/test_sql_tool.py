import pytest
from app.integrations.mock_snowflake import query_metrics, get_service_summary, get_degraded_events
from app.tools.sql_tool import SQLTool


def test_query_metrics_all():
    results = query_metrics()
    assert len(results) > 0


def test_query_by_service():
    results = query_metrics(service="payment-api")
    assert all(r["service_name"] == "payment-api" for r in results)


def test_query_by_status():
    results = query_metrics(status="degraded")
    assert all(r["status"] == "degraded" for r in results)
    assert len(results) > 0


def test_query_date_range():
    results = query_metrics(service="payment-api", date_from="2026-04-14", date_to="2026-04-16")
    assert len(results) == 2
    assert any(r["status"] == "degraded" for r in results)


def test_date_is_string_not_timestamp(tmp_path):
    """Ensure dates are JSON-safe strings, not pandas Timestamps."""
    results = query_metrics(service="payment-api", limit=5)
    for r in results:
        assert isinstance(r["date"], str), f"date should be str, got {type(r['date'])}"


def test_service_summary():
    summary = get_service_summary("payment-api")
    assert summary["service"] == "payment-api"
    assert summary["degraded_days"] >= 3
    assert summary["avg_latency_ms"] > 0


def test_service_summary_unknown():
    summary = get_service_summary("nonexistent-service")
    assert "error" in summary


def test_degraded_events():
    events = get_degraded_events()
    assert len(events) > 0
    assert all(r["status"] == "degraded" for r in events)


def test_degraded_events_filtered():
    events = get_degraded_events(service="payment-api")
    assert all(r["service_name"] == "payment-api" for r in events)


def test_sql_tool_was_degraded_on():
    tool = SQLTool()
    result = tool.was_degraded_on("payment-api", "2026-04-15")
    assert result["found"] is True
    assert result["status"] == "degraded"
    assert result["latency_ms"] == 1890


def test_sql_tool_was_healthy():
    tool = SQLTool()
    result = tool.was_degraded_on("payment-api", "2026-04-16")
    assert result["found"] is True
    assert result["status"] == "healthy"
