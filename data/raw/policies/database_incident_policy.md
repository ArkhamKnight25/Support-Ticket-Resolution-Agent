# Database Incident Response Policy

## Purpose
This policy defines the standard procedures for detecting, responding to, and recovering from database incidents across all production environments. It applies to all relational databases (MySQL, PostgreSQL) and data warehouses (Snowflake) operated by the engineering team.

## Scope
This policy covers:
- Production databases for all customer-facing services
- Internal operational databases
- Data warehouse environments

---

## Severity Classifications

### P1 — Critical (Immediate Response Required)
- Complete database outage (no connections accepted)
- Data corruption detected
- Security breach or unauthorized access
- More than 50% of read or write operations failing
- **Response time: 5 minutes**

### P2 — High
- Degraded performance affecting customer experience (latency > 3x baseline)
- Replication lag > 60 seconds
- Disk usage > 85%
- **Response time: 15 minutes**

### P3 — Medium
- Non-critical query performance degradation
- Replication lag between 30–60 seconds
- Disk usage between 75–85%
- **Response time: 1 hour**

---

## Response Procedures

### Step 1: Acknowledge and Assess (0–5 minutes)
1. Acknowledge the alert in PagerDuty
2. Log into the database monitoring dashboard (Grafana/DataDog)
3. Identify the affected database instance and service
4. Determine if the incident is P1, P2, or P3
5. Post an initial update in #incident-response Teams channel: include what is affected, severity, and that investigation has started

### Step 2: Diagnose (5–15 minutes)
1. Check current active connections and locks:
   ```sql
   SELECT * FROM information_schema.processlist WHERE command != 'Sleep' ORDER BY time DESC;
   ```
2. Check for long-running queries:
   ```sql
   SELECT * FROM information_schema.processlist WHERE time > 30 ORDER BY time DESC;
   ```
3. Check disk usage on the database server
4. Review the database error log for recent errors
5. Check replication status (if applicable): `SHOW SLAVE STATUS\G`

### Step 3: Contain (15–30 minutes)
1. Kill blocking queries if they are causing cascading failures:
   ```sql
   KILL QUERY [process_id];
   ```
2. If disk is critically full — identify and purge old binary logs:
   ```sql
   PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 3 DAY);
   ```
3. If under attack or unauthorized access — immediately revoke credentials and notify the Security team
4. If replication is broken — pause writes to the replica and resync

### Step 4: Resolve and Verify
1. Confirm the root cause has been addressed
2. Monitor key metrics for 30 minutes to confirm stability
3. Post a recovery update in #incident-response

---

## Post-Incident Requirements

All P1 and P2 incidents require a post-mortem within 48 hours including:
- Timeline of events
- Root cause analysis
- Impact assessment
- Action items to prevent recurrence

---

## Escalation Contacts
- On-call DBA: Check PagerDuty rotation
- Database Platform Team Lead: db-lead@company.com
- CTO (P1 only): cto@company.com
