# System Monitoring Guide

## Overview
This guide describes the monitoring stack, key metrics to watch, and how to respond to common alert types across all production services.

## Monitoring Stack
- **Metrics:** Prometheus + Grafana
- **Logs:** Elasticsearch + Kibana (ELK stack)
- **Alerts:** PagerDuty (on-call routing) + MS Teams (channel notifications)
- **Uptime:** Pingdom (external availability checks)
- **Tracing:** Jaeger (distributed traces)

---

## Key Dashboards

| Dashboard | URL | Purpose |
|---|---|---|
| Services Overview | grafana/d/services-overview | All services health at a glance |
| Payment API | grafana/d/payment-api | Payment API latency, error rate, throughput |
| Database | grafana/d/database | Query performance, connections, replication |
| Infrastructure | grafana/d/infra | CPU, memory, disk across all nodes |
| Business Metrics | grafana/d/business | Orders, payments, user signups (real-time) |

---

## Critical Metrics and Thresholds

### Latency
- **p50 (median) latency:** Should be < 100ms for most endpoints
- **p99 latency:** Alert if > 500ms for more than 2 minutes
- **p99.9 latency:** Alert if > 2000ms for any duration

### Error Rates
- **5xx error rate:** Alert if > 0.5% over 2 minutes
- **4xx error rate:** Informational — investigate if > 5% as it may indicate a client-side bug or abuse

### Throughput
- **Requests per second (RPS):** Know your baseline. Alert if drops > 30% unexpectedly (may indicate upstream issue or traffic loss).
- **Queue depth:** Alert if job queues grow beyond 1000 items

### Infrastructure
- **CPU usage:** Alert if > 85% for 5 minutes
- **Memory usage:** Alert if > 80% for 5 minutes
- **Disk usage:** Alert if > 75% (warning), > 90% (critical)
- **Pod restarts:** Alert if any pod restarts > 3 times in 10 minutes

---

## Alert Response Procedures

### High Latency Alert

1. Check the service dashboard — identify which endpoint is slow
2. Check database query times — are there slow queries?
3. Check external dependency latency (third-party APIs, payment gateways)
4. Check if a recent deployment correlates with the latency increase
5. If database-related: check connection pool usage and slow query log
6. If deployment-related: consider rollback

### High Error Rate Alert

1. Check error logs in Kibana — identify the exception type and stack trace
2. Check if the error is isolated to one endpoint or service-wide
3. Check recent deployments and config changes
4. Check downstream services — is a dependency failing?
5. If it is a known bug with a fix available — deploy the fix
6. If cause is unknown — engage the on-call engineer immediately

### CPU/Memory Spike Alert

1. Identify which pods or nodes are affected
2. Check if traffic has increased unexpectedly (DDoS, viral event)
3. Check for runaway processes: `kubectl top pods`
4. If caused by traffic: scale up the affected deployment
5. If caused by a runaway process: restart the affected pod and investigate

---

## Log Analysis

### Finding errors in Kibana
```
service: payment-api AND level: ERROR AND @timestamp: [now-1h TO now]
```

### Finding slow requests
```
service: payment-api AND response_time_ms: >1000 AND @timestamp: [now-15m TO now]
```

### Finding database errors
```
service: payment-api AND message: "database" AND level: ERROR
```

---

## Escalation Guidelines

| Situation | First Contact | Escalate If |
|---|---|---|
| Service latency spike | On-call engineer | Not resolved in 15 min → team lead |
| Error rate > 1% | On-call engineer | Not resolved in 10 min → team lead |
| Complete outage | On-call engineer immediately | Also notify manager after 5 min |
| Security alert | Security team immediately | Do not attempt self-remediation |
| Data loss risk | DBA + Security + Manager | All hands |

---

## Useful Commands

```bash
# Check all pod health
kubectl get pods --all-namespaces

# View resource usage
kubectl top pods
kubectl top nodes

# Stream logs from a service
kubectl logs -f -l app=payment-api

# Check recent events (errors, warnings)
kubectl get events --sort-by='.lastTimestamp' | tail -20

# Describe a failing pod
kubectl describe pod [pod-name]
```
