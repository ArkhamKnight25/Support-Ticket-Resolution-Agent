# Error Analysis

Generated: 2026-06-01T06:55:10.877379Z


**9 failed out of 20 questions.**


### What is the escalation procedure for a P1 database incident?
- Category: rag  Difficulty: medium
- Expected intent: `document_question` | Got: `incident_analysis`
- Expected tool: `rag_tool` | Got: `ticket_tool,rag_tool,sql_tool`
- Keyword score: 0.25 | Retrieval hit: True

### How do I roll back a bad deployment?
- Category: rag  Difficulty: easy
- Expected intent: `document_question` | Got: `document_question`
- Expected tool: `rag_tool` | Got: `rag_tool`
- Keyword score: 0.25 | Retrieval hit: True

### What monitoring alerts should trigger for high CPU usage?
- Category: rag  Difficulty: medium
- Expected intent: `document_question` | Got: `document_question`
- Expected tool: `rag_tool` | Got: `rag_tool`
- Keyword score: 0.25 | Retrieval hit: True

### What are the data retention requirements for payment records?
- Category: rag  Difficulty: easy
- Expected intent: `document_question` | Got: `document_question`
- Expected tool: `rag_tool` | Got: `rag_tool`
- Keyword score: 0.0 | Retrieval hit: True

### What should I do before a production deployment?
- Category: rag  Difficulty: easy
- Expected intent: `document_question` | Got: `document_question`
- Expected tool: `rag_tool` | Got: `rag_tool`
- Keyword score: 0.25 | Retrieval hit: True

### What was the root cause of INC-1001?
- Category: ticket  Difficulty: easy
- Expected intent: `incident_analysis` | Got: `incident_analysis`
- Expected tool: `ticket_tool` | Got: `ticket_tool,rag_tool,sql_tool`
- Keyword score: 0.333 | Retrieval hit: False

### Was there a database failover incident?
- Category: ticket  Difficulty: hard
- Expected intent: `incident_analysis` | Got: `incident_analysis`
- Expected tool: `ticket_tool` | Got: `ticket_tool,rag_tool,sql_tool`
- Keyword score: 0.25 | Retrieval hit: False

### What services were degraded in April 2026?
- Category: metrics  Difficulty: hard
- Expected intent: `metrics_question` | Got: `metrics_question`
- Expected tool: `sql_tool` | Got: `sql_tool`
- Keyword score: 0.333 | Retrieval hit: False

### Write an incident notification for the operations team
- Category: teams  Difficulty: easy
- Expected intent: `communication_request` | Got: `communication_request`
- Expected tool: `teams_tool` | Got: `ticket_tool,rag_tool,sql_tool,teams_tool`
- Keyword score: 0.0 | Retrieval hit: False
