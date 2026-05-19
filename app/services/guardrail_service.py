import re
from app.config import Settings
from app.services.logging_service import get_logger

logger = get_logger(__name__)

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\b.{0,30}\binstructions",
    r"forget (the |your |all )?instructions",
    r"disregard (the |your |all )?instructions",
    r"reveal (your |the )?system prompt",
    r"you are now",
    r"new persona",
    r"act as (if you are|an? )",
    r"pretend (you are|to be)",
    r"bypass (safety|filter|guardrail)",
    r"jailbreak",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# Basic PII patterns
_PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"), "[CARD]"),
]


class GuardrailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def check_input(self, message: str) -> bool:
        """Returns True if the message should be blocked."""
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(message):
                logger.warning("Prompt injection detected", pattern=pattern.pattern)
                return True
        return False

    async def check_output(self, response: str, context_docs: list) -> bool:
        """
        Returns True if the output looks weakly grounded.

        This is a lightweight heuristic, not a formal verifier: it checks for
        missing context and very low token overlap between the response and the
        retrieved evidence.
        """
        if not context_docs:
            logger.warning("output_check_no_context_docs")
            return True

        context_text = " ".join(
            getattr(doc, "page_content", "")
            if hasattr(doc, "page_content")
            else str(doc.get("text", ""))
            for doc in context_docs
        ).lower()
        context_tokens = {token for token in re.findall(r"[a-z0-9_-]{4,}", context_text)}
        response_tokens = {token for token in re.findall(r"[a-z0-9_-]{4,}", response.lower())}

        if not response_tokens:
            return True

        overlap = len(response_tokens & context_tokens) / max(len(response_tokens), 1)
        if overlap < 0.12:
            logger.warning("output_check_low_overlap", overlap=round(overlap, 3))
            return True

        return False

    def mask_pii(self, text: str) -> str:
        """Redact common PII patterns from text."""
        for pattern, replacement in _PII_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def build_warnings(
        self,
        *,
        context_docs: list,
        confidence: str | None,
        requires_human_approval: bool,
        output_flagged: bool,
    ) -> list[str]:
        warnings: list[str] = []
        if not context_docs:
            warnings.append("No supporting documents were retrieved for this response.")
        if confidence == "low":
            warnings.append("Low-confidence response. Validate against source systems before acting.")
        if output_flagged:
            warnings.append("Output grounding check flagged this response for manual review.")
        if requires_human_approval:
            warnings.append("External communication requires human approval before sending.")
        return warnings
