"""
Quick smoke-test for Phase 2 — Bedrock connection.
Run: python scripts/test_bedrock.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.services.bedrock_service import BedrockService


async def main():
    print(f"Region  : {settings.AWS_REGION}")
    print(f"Model   : {settings.BEDROCK_CHAT_MODEL_ID}")
    print(f"Key set : {'yes' if settings.AWS_ACCESS_KEY_ID else 'NO - add to .env'}")
    print()

    svc = BedrockService(settings)

    print("Sending test prompt to Bedrock...")
    try:
        result = await svc.chat(
            message="Explain what an incident runbook is in 3 bullet points.",
            context_docs=[],
            history=[],
        )
        print(f"\nResponse ({result.latency_ms:.0f}ms):")
        print(result.content)
        print(f"\nTokens — input: {result.input_tokens}, output: {result.output_tokens}")
        print("\nPhase 2 PASSED")
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        print("\nSee AWS manual steps in docs/implementation_plan.md — Phase 2")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
