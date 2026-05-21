import pytest

from app.config import settings
from app.services.guardrail_service import GuardrailService


@pytest.mark.asyncio
async def test_output_check_flags_empty_context():
    guardrail = GuardrailService(settings)
    flagged = await guardrail.check_output("This definitely happened in production.", [])
    assert flagged is True


@pytest.mark.asyncio
async def test_output_check_accepts_grounded_overlap():
    guardrail = GuardrailService(settings)
    docs = [{"text": "Payment API timeout runbook says to check the database connection pool."}]
    flagged = await guardrail.check_output(
        "Check the database connection pool for the payment API timeout issue.",
        docs,
    )
    assert flagged is False


def test_build_warnings_combines_operational_flags():
    guardrail = GuardrailService(settings)
    warnings = guardrail.build_warnings(
        context_docs=[],
        confidence="low",
        requires_human_approval=True,
        output_flagged=True,
    )
    assert len(warnings) == 4
    assert any("human approval" in warning.lower() for warning in warnings)
