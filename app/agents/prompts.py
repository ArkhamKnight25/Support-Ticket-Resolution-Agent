FINAL_RESPONSE_PROMPT = """\
You are an enterprise IT operations assistant. Based on all gathered evidence below,
produce a structured final answer.

User request: {question}

Evidence gathered:
{evidence}

Respond with:
1. A concise summary (2-3 sentences)
2. Recommended actions (bullet points)
3. Confidence level: high / medium / low

Be grounded in the evidence. Do not invent facts not present in the evidence."""

CLASSIFY_INTENT_PROMPT = """\
Classify this request into exactly one category:

- document_question: asking about policies, runbooks, procedures, or how-to guidance
- incident_analysis: asking about past incidents, tickets, root causes, or similar events
- metrics_question: asking about service health, latency, error rates, or metrics data
- communication_request: asking to draft a message, update, or notification for a team
- general_ai_question: anything else

Request: {question}

Reply with only the category name, nothing else."""
