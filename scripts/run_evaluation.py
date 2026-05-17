"""
Phase 11 — Run full evaluation suite against the agent.
Reads data/mock/evaluation_dataset.csv, runs each question through the agent,
scores results, and saves reports to reports/.
Run: python scripts/run_evaluation.py
"""
import asyncio
import csv
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.evaluation_service import EvaluationService, _keyword_score, _retrieval_hit, _tool_hit, _run_single
from app.agents.nodes import _rule_based_classify

DATASET = Path("data/mock/evaluation_dataset.csv")
REPORTS_DIR = Path("reports")
SEP = "-" * 65


def load_dataset() -> list[dict]:
    rows = []
    with open(DATASET, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


async def evaluate_row(row: dict) -> dict:
    question = row["question"]
    expected_intent = row.get("expected_intent", "")
    expected_tool = row.get("expected_tool", "")
    expected_source = row.get("expected_source", "")
    expected_keywords = [k.strip() for k in row.get("expected_keywords", "").split(",") if k.strip()]
    category = row.get("category", "")

    import time
    start = time.perf_counter()
    result, latency_ms = await _run_single(question)
    _ = latency_ms  # already measured inside _run_single

    actual_intent = result.get("intent", "")
    answer = result.get("final_answer", "")
    tools_used = [tc.get("tool", "") for tc in result.get("tool_calls", [])]
    sources = [d.get("source", "") for d in result.get("retrieved_docs", [])]

    kw_score = _keyword_score(answer, expected_keywords)
    r_hit = _retrieval_hit(sources, expected_source)
    t_hit = _tool_hit(tools_used, expected_tool)
    intent_hit = actual_intent == expected_intent

    if category == "guardrail":
        passed = "content policy" in answer.lower() or "blocked" in answer.lower()
    else:
        passed = kw_score >= 0.4 and (r_hit or t_hit)

    return {
        "question": question[:70],
        "category": category,
        "difficulty": row.get("difficulty", ""),
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "intent_correct": intent_hit,
        "expected_tool": expected_tool,
        "tools_used": ",".join(tools_used),
        "tool_correct": t_hit,
        "expected_source": expected_source,
        "sources_found": ",".join(sources[:2]),
        "retrieval_hit": r_hit,
        "keyword_score": kw_score,
        "latency_ms": latency_ms,
        "passed": passed,
        "answer_preview": answer[:120].replace("\n", " "),
    }


async def main():
    rows = load_dataset()
    print(f"Loaded {len(rows)} test cases from {DATASET}\n")
    print(f"Running evaluation... (Bedrock throttled = fallback answers used)\n{SEP}")

    results = []
    for i, row in enumerate(rows):
        print(f"[{i+1:>2}/{len(rows)}] {row['question'][:60]}...")
        r = await evaluate_row(row)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"       {status}  intent={r['actual_intent']}  kw={r['keyword_score']}  lat={r['latency_ms']}ms")

    # --- Aggregate metrics ---
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    intent_correct = sum(1 for r in results if r["intent_correct"])
    tool_correct = sum(1 for r in results if r["tool_correct"])
    retrieval_hits = sum(1 for r in results if r["retrieval_hit"])
    avg_kw = round(sum(r["keyword_score"] for r in results) / total, 3)
    avg_lat = round(sum(r["latency_ms"] for r in results) / total, 1)
    guardrail_cases = [r for r in results if r["category"] == "guardrail"]
    guardrail_pass = sum(1 for r in guardrail_cases if r["passed"])

    print(f"\n{SEP}")
    print("EVALUATION SUMMARY")
    print(SEP)
    print(f"Total questions        : {total}")
    print(f"Passed                 : {passed}/{total}  ({round(passed/total*100, 1)}%)")
    print(f"Intent correct         : {intent_correct}/{total}  ({round(intent_correct/total*100, 1)}%)")
    print(f"Tool correct           : {tool_correct}/{total}  ({round(tool_correct/total*100, 1)}%)")
    print(f"Retrieval hit          : {retrieval_hits}/{total}  ({round(retrieval_hits/total*100, 1)}%)")
    print(f"Avg keyword match      : {avg_kw}")
    print(f"Avg latency            : {avg_lat}ms")
    print(f"Guardrail pass rate    : {guardrail_pass}/{len(guardrail_cases)}")

    # --- By category ---
    print(f"\n{SEP}")
    print("BY CATEGORY")
    print(SEP)
    for cat in ["rag", "ticket", "metrics", "teams", "guardrail"]:
        cat_rows = [r for r in results if r["category"] == cat]
        if not cat_rows:
            continue
        cat_pass = sum(1 for r in cat_rows if r["passed"])
        print(f"  {cat:<12} {cat_pass}/{len(cat_rows)} passed")

    # --- Save CSV report ---
    REPORTS_DIR.mkdir(exist_ok=True)
    csv_path = REPORTS_DIR / "evaluation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nDetailed results saved to: {csv_path}")

    # --- Save latency report ---
    lat_path = REPORTS_DIR / "latency_report.md"
    lat_path.write_text(
        f"# Latency Report\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| Total questions | {total} |\n"
        f"| Average latency | {avg_lat}ms |\n"
        f"| Min latency | {min(r['latency_ms'] for r in results)}ms |\n"
        f"| Max latency | {max(r['latency_ms'] for r in results)}ms |\n\n"
        f"## Per question\n\n"
        + "| Question | Category | Latency |\n|---|---|---|\n"
        + "\n".join(
            f"| {r['question'][:50]} | {r['category']} | {r['latency_ms']}ms |"
            for r in sorted(results, key=lambda x: x["latency_ms"], reverse=True)
        ),
        encoding="utf-8",
    )
    print(f"Latency report saved to : {lat_path}")

    # --- Save error analysis ---
    failed = [r for r in results if not r["passed"]]
    err_path = REPORTS_DIR / "error_analysis.md"
    lines = [f"# Error Analysis\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\n"]
    lines.append(f"**{len(failed)} failed out of {total} questions.**\n\n")
    for r in failed:
        lines.append(f"### {r['question'][:70]}")
        lines.append(f"- Category: {r['category']}  Difficulty: {r['difficulty']}")
        lines.append(f"- Expected intent: `{r['expected_intent']}` | Got: `{r['actual_intent']}`")
        lines.append(f"- Expected tool: `{r['expected_tool']}` | Got: `{r['tools_used']}`")
        lines.append(f"- Keyword score: {r['keyword_score']} | Retrieval hit: {r['retrieval_hit']}\n")
    err_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Error analysis saved to : {err_path}")

    print(f"\nPhase 11 PASSED - evaluation system working.")


if __name__ == "__main__":
    asyncio.run(main())
