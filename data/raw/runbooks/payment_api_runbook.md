# Payment API Runbook

## Overview
The Payment API is a critical service responsible for processing all customer payment transactions. It communicates with the internal transaction database and external payment gateways (Stripe, PayPal). Any degradation in this service has direct revenue impact and must be treated as P1.

## Service Details
- **Service name:** payment-api
- **Owner team:** Payments Engineering
- **On-call contact:** payments-oncall@company.com
- **SLA:** 99.95% uptime, p99 latency < 500ms

---

## Common Incidents and Resolutions

### Incident Type 1: Timeout Errors (504 Gateway Timeout)

**Symptoms:**
- API returns HTTP 504 to clients
- Error logs show `connection timeout` or `read timeout`
- Latency metrics spike above 2000ms

**Diagnosis steps:**
1. Check the payment-api latency dashboard in Grafana
2. Check database connection pool usage — run `SHOW STATUS LIKE 'Threads_connected'` on the transactions DB
3. Check the external gateway status pages (Stripe: status.stripe.com, PayPal: www.paypal-status.com)
4. Check the payment-api pod logs: `kubectl logs -l app=payment-api --tail=200`
5. Look for slow query logs in MySQL: `SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 20`

**Resolution steps:**
1. If database connection pool is exhausted (> 80% of max_connections):
   - Increase pool size in `config/database.yml`: set `pool_size` from 10 to 50
   - Restart the payment-api pods: `kubectl rollout restart deployment/payment-api`
2. If slow queries are identified:
   - Add appropriate database indexes
   - Optimize the slow query with the DBA team
3. If external gateway is down:
   - Switch traffic to the secondary gateway (see Gateway Failover Runbook)
   - Post incident update to the #operations-alerts Teams channel

**Escalation path:**
- L1: On-call engineer (first 15 minutes)
- L2: Payments team lead (if not resolved in 15 minutes)
- L3: Database operations team (if DB-related)

---

### Incident Type 2: High Error Rate (5xx responses)

**Symptoms:**
- Error rate above 1% in the Grafana dashboard
- Increased `payment_failed` events in the event log
- Customer complaints about failed payments

**Diagnosis steps:**
1. Check error rate metric: `payment_api_error_rate_5m`
2. Check recent deployments: `kubectl rollout history deployment/payment-api`
3. Review error logs for exception types
4. Check downstream service health (fraud detection, notification service)

**Resolution steps:**
1. If caused by a recent deployment — roll back: `kubectl rollout undo deployment/payment-api`
2. If caused by a downstream service failure — enable the circuit breaker flag in the feature flag system
3. If caused by a database schema issue — contact DBA immediately

---

### Incident Type 3: Memory Leak / OOM Kills

**Symptoms:**
- Pods are being OOM-killed (check `kubectl describe pod`)
- Memory usage climbing steadily without release
- Latency gradually increasing over hours

**Diagnosis steps:**
1. Check pod memory usage: `kubectl top pods -l app=payment-api`
2. Check for memory leak patterns in heap dumps
3. Review recent code changes for unbounded caches or connection leaks

**Resolution steps:**
1. Immediate: Restart affected pods to clear memory
2. Short-term: Increase memory limits in the pod spec
3. Long-term: Profile the application and fix the memory leak

---

## Monitoring and Alerts

| Alert | Threshold | Action |
|---|---|---|
| payment_api_latency_p99 | > 500ms for 5min | Check DB and gateway |
| payment_api_error_rate | > 1% for 2min | Check logs and deployments |
| payment_api_connection_pool | > 80% for 3min | Increase pool size |
| payment_api_pod_restarts | > 3 in 10min | Check OOM and logs |

---

## Useful Commands

```bash
# Check service health
kubectl get pods -l app=payment-api

# View recent logs
kubectl logs -l app=payment-api --tail=200 --since=1h

# Check database connections
mysql -u admin -p -e "SHOW STATUS LIKE 'Threads_connected';"

# Restart the service
kubectl rollout restart deployment/payment-api

# Scale up pods
kubectl scale deployment/payment-api --replicas=5
```

---

## Related Runbooks
- Database Connection Pool Management Runbook
- External Gateway Failover Runbook
- Kubernetes Pod Restart Runbook
