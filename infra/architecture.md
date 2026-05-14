# AWS Architecture

This document describes how the Enterprise AI Ops Copilot runs in production on AWS. The local version (ChromaDB + mock integrations) maps onto managed AWS services as follows.

---

## High-Level Architecture

```
                          ┌─────────────────────────┐
                          │   Users / Frontend /     │
                          │   Swagger UI             │
                          └────────────┬────────────┘
                                       │ HTTPS
                                       ▼
                          ┌─────────────────────────┐
                          │   Application Load       │
                          │   Balancer (ALB)         │
                          └────────────┬────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │   ECS Fargate Service    │
                          │   (FastAPI + LangGraph)  │
                          └────────────┬────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │  Amazon Bedrock  │   │  Amazon          │   │  Integrations    │
   │  (Claude +       │   │  OpenSearch      │   │  (ServiceNow,    │
   │   Titan Embed)   │   │  (vector store)  │   │   Snowflake,     │
   │                  │   │                  │   │   MS Teams)      │
   └──────────────────┘   └──────────────────┘   └──────────────────┘
              │                        ▲
              │ Guardrails             │ vectors
              ▼                        │
   ┌──────────────────┐                │
   │  Bedrock         │                │
   │  Guardrails      │                │
   └──────────────────┘                │
                                       │
                          ═════════════╪═══════════════════════
                          Ingestion Pipeline (async)
                          ═════════════╪═══════════════════════
                                       │
   ┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────────┐
   │ Amazon   │──▶│ Amazon     │──▶│ AWS Step     │──▶│ Lambda +     │
   │ S3       │   │ EventBridge│   │ Functions    │   │ ECS Embedding│
   │ (docs)   │   │ (trigger)  │   │ (orchestrate)│   │ Job          │
   └──────────┘   └────────────┘   └──────────────┘   └──────┬───────┘
                                                              │
                                                              ▼
                                                  ┌──────────────────┐
                                                  │  Amazon          │
                                                  │  OpenSearch      │
                                                  └──────────────────┘
```

---

## Component Mapping: Local → AWS

| Local (dev) | AWS (production) | Purpose |
|---|---|---|
| FastAPI via uvicorn | ECS Fargate behind ALB | Serve the API |
| ChromaDB (local files) | Amazon OpenSearch Service | Vector store for RAG |
| ChromaDB local embeddings | Amazon Bedrock Titan Embeddings | Generate embeddings |
| `data/raw/` local files | Amazon S3 bucket | Document storage |
| `scripts/ingest_documents.py` | Step Functions + Lambda + ECS | Async ingestion pipeline |
| Mock ServiceNow/Snowflake/Teams | Real APIs via Secrets Manager creds | Enterprise integrations |
| structlog to stdout | CloudWatch Logs | Centralized logging |
| `.env` file | AWS Secrets Manager + SSM Parameter Store | Configuration & secrets |

---

## Request Flow (Runtime — Chat/Agent)

1. User sends a request to the ALB over HTTPS.
2. ALB routes to a healthy ECS Fargate task running the FastAPI app.
3. The LangGraph agent classifies intent and calls tools:
   - **RAG** → embeds the query via Bedrock Titan, searches OpenSearch.
   - **Tickets/Metrics/Teams** → calls the real or mock integration.
4. Evidence is merged and passed to **Amazon Bedrock (Claude)** for the final response.
5. **Bedrock Guardrails** screen the input and output.
6. The structured response returns to the user. Logs/metrics flow to CloudWatch.

---

## Ingestion Flow (Async — Document Upload)

1. A document is uploaded to the **S3** `documents/` prefix.
2. **EventBridge** detects the `s3:ObjectCreated` event and starts a **Step Functions** execution.
3. The state machine runs:
   - `ValidateDocument` (Lambda) — checks file type, size, and content.
   - `ExtractText` — pulls raw text (Textract for PDFs if needed).
   - `ChunkDocument` — splits into overlapping chunks.
   - `GenerateEmbeddings` (ECS task) — calls Bedrock Titan for each chunk.
   - `UpdateVectorIndex` — upserts vectors into OpenSearch.
   - `SaveIngestionLog` — writes a record to DynamoDB/CloudWatch.
4. On failure at any step, the execution routes to a `HandleFailure` state that alerts via SNS.

See [aws_stepfunctions_definition.json](aws_stepfunctions_definition.json) for the full state machine.

---

## Security

- **IAM least privilege** — the ECS task role can only call Bedrock, read the specific S3 bucket, and read/write the OpenSearch domain.
- **Secrets** — integration credentials live in AWS Secrets Manager, never in env vars or code.
- **Network** — ECS tasks run in private subnets; only the ALB is public. OpenSearch is VPC-internal.
- **Guardrails** — Bedrock Guardrails enforce content policy at the model boundary.
- **Encryption** — S3, OpenSearch, and Secrets Manager all use encryption at rest (KMS).

---

## Scaling

- **ECS Fargate** auto-scales on CPU/memory and request count via Application Auto Scaling.
- **OpenSearch** scales by adding data nodes; use UltraWarm for older vectors.
- **Bedrock** is fully managed — request a quota increase for higher throughput.
- **Ingestion** scales horizontally — Step Functions runs one execution per uploaded document in parallel.

---

## Cost Notes

The expensive components if left running:
- **OpenSearch** — at least one always-on data node (~$25/mo for `t3.small.search`).
- **ECS Fargate** — per-task hourly cost; scale to zero off-hours for dev.
- **NAT Gateway** — hourly + data charges; the most common surprise cost.
- **Bedrock** — pay-per-token; negligible for demos, scales with usage.

For a portfolio demo, the Terraform here defines the resources but you do not need to `terraform apply` — having the IaC written demonstrates the competency without incurring cost.
