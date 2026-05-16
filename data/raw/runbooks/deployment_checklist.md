# Production Deployment Checklist

## Purpose
This checklist must be completed before every production deployment. It is designed to catch common deployment failures and ensure a safe, reversible release process.

## Pre-Deployment (Day Before)

### Code Readiness
- [ ] All related pull requests are merged to the main branch
- [ ] CI/CD pipeline passes all tests (unit, integration, contract)
- [ ] Code has been reviewed and approved by at least 2 engineers
- [ ] No known critical bugs in the release
- [ ] Database migrations are tested on staging with production-sized data

### Coordination
- [ ] Deployment window is scheduled and communicated to the team
- [ ] On-call engineer is aware and available during deployment
- [ ] Customer support team is notified if user-facing changes are included
- [ ] Rollback plan is documented and tested

### Environment
- [ ] Staging deployment was successful in the last 24 hours
- [ ] Performance tests show no regression from baseline
- [ ] All environment variables and secrets are updated in the target environment
- [ ] Feature flags are configured correctly

---

## Deployment Day

### 30 Minutes Before
- [ ] Confirm all systems are healthy (no active P1 or P2 incidents)
- [ ] Verify the deployment artifact (Docker image) matches the approved commit SHA
- [ ] Open monitoring dashboards: Grafana, PagerDuty, error rate alerts
- [ ] Notify #deployments Teams channel: "Starting deployment of [service] v[version] at [time]"

### During Deployment
- [ ] Deploy to canary (5% of traffic) first if canary deployment is enabled
- [ ] Monitor error rates and latency for 5 minutes on canary
- [ ] If canary looks healthy, proceed with full rollout
- [ ] Watch deployment progress: `kubectl rollout status deployment/[service-name]`

### Verification (Within 15 Minutes of Deployment)
- [ ] All pods are running and healthy: `kubectl get pods -l app=[service-name]`
- [ ] Health check endpoint returns 200: `curl https://[service]/health`
- [ ] Key business metrics are within normal range (orders processed, payment success rate)
- [ ] No spike in error rate or latency in Grafana
- [ ] No new alerts firing in PagerDuty

---

## Rollback Procedure

If any check fails during or after deployment:

1. Immediately notify the team in #deployments
2. Roll back the Kubernetes deployment:
   ```bash
   kubectl rollout undo deployment/[service-name]
   ```
3. Verify rollback is successful: `kubectl rollout status deployment/[service-name]`
4. If database migrations were applied, run the down migration:
   ```bash
   python manage.py migrate [app] [previous_migration]
   ```
5. Confirm service is healthy with the previous version
6. Post incident summary in #deployments channel

---

## Post-Deployment (1 Hour After)

- [ ] No new alerts or error spikes in the hour following deployment
- [ ] Deployment marked as successful in the deployment log
- [ ] Release notes shared with the team
- [ ] Any temporary feature flags cleaned up within 7 days
