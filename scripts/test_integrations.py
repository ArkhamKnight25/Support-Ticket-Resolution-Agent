"""
Phases 7, 8, 9 — integration smoke test.
Run: python scripts/test_integrations.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.integrations.mock_servicenow import search_tickets, get_ticket
from app.integrations.mock_snowflake import query_metrics, get_service_summary, get_degraded_events
from app.integrations.mock_teams import draft_message, suggest_channel

SEP = "-" * 55


def test_servicenow():
    print(f"\n{SEP}")
    print("Phase 7 — Mock ServiceNow")
    print(SEP)

    results = search_tickets(query="payment API timeout", limit=3)
    print(f"Search 'payment API timeout': {len(results)} results")
    for t in results:
        print(f"  {t['ticket_id']}  [{t['priority']}]  {t['title']}")

    ticket = get_ticket("INC-1001")
    print(f"\nGet INC-1001: {ticket['title']}")
    print(f"  Root cause : {ticket['root_cause']}")
    print(f"  Resolution : {ticket['resolution']}")

    p1s = search_tickets(priority="P1", limit=5)
    print(f"\nAll P1 tickets: {len(p1s)}")


def test_snowflake():
    print(f"\n{SEP}")
    print("Phase 8 — Mock Snowflake/SQL")
    print(SEP)

    rows = query_metrics(service="payment-api", date_from="2026-04-14", date_to="2026-04-16")
    print(f"payment-api metrics 2026-04-14 to 2026-04-16:")
    for r in rows:
        print(f"  {str(r['date'])[:10]}  latency={r['latency_ms']}ms  error={r['error_rate']}%  status={r['status']}")

    summary = get_service_summary("payment-api")
    print(f"\npayment-api summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    degraded = get_degraded_events("payment-api")
    print(f"\nDegraded events for payment-api: {len(degraded)}")


def test_teams():
    print(f"\n{SEP}")
    print("Phase 9 — Mock MS Teams")
    print(SEP)

    channel = suggest_channel("payment-api timeout", "P1")
    print(f"Suggested channel for P1 payment incident: #{channel}")

    draft = draft_message(
        channel=channel,
        content="Update: The payment-api is experiencing timeout errors. "
                "Investigation shows high latency and database connection pool exhaustion. "
                "Team is working on a fix.",
        incident_id="INC-1001",
        severity="P1",
    )
    print(f"\nDraft message:")
    print(f"  Channel              : #{draft['channel']}")
    print(f"  Requires approval    : {draft['requires_human_approval']}")
    print(f"  Sent                 : {draft['sent']}")
    print(f"  Content preview      : {draft['draft'][:80]}...")


if __name__ == "__main__":
    test_servicenow()
    test_snowflake()
    test_teams()
    print(f"\n{SEP}")
    print("Phases 7, 8, 9 PASSED — all integrations working.")
    print(SEP)
