# Customer Data Handling Policy

## Purpose
This policy defines the rules and responsibilities for handling customer data within our systems. All engineers, data analysts, and operations staff must follow these guidelines to ensure compliance with GDPR, CCPA, and internal data governance standards.

## Data Classification

### Class 1 — Highly Sensitive (Restricted)
- Payment card numbers (PAN)
- Bank account numbers
- Social Security / National ID numbers
- Passwords and authentication credentials
- **Handling:** Must be encrypted at rest and in transit. Access is logged. Only authorized personnel with a business need may access this data.

### Class 2 — Personal Data (Confidential)
- Full names
- Email addresses
- Phone numbers
- IP addresses
- Physical addresses
- **Handling:** Must be encrypted in transit. Access requires role-based authorization. Cannot be exported without approval.

### Class 3 — Internal Use Only
- Aggregated analytics
- Service metrics
- Internal logs (without PII)
- **Handling:** Available to all internal staff but must not be shared externally.

---

## Principles

### Data Minimization
Only collect data that is strictly necessary for the stated business purpose. Do not store data beyond its required retention period.

### Purpose Limitation
Data collected for one purpose must not be used for a different purpose without explicit consent or legal basis.

### Access Control
Access to customer data must follow the principle of least privilege. Engineers should not have direct production database access unless required for an active incident, and all such access must be logged.

### Retention
| Data Type | Retention Period |
|---|---|
| Payment transaction records | 7 years |
| Customer account data | Duration of account + 2 years |
| Support interaction logs | 3 years |
| Authentication logs | 1 year |
| Application error logs | 90 days |

---

## Incident Response for Data Breaches

If a data breach involving Class 1 or Class 2 data is suspected:

1. **Immediately** notify the Security team at security@company.com
2. **Do not** attempt to investigate or remediate without Security team involvement
3. **Preserve** all logs and evidence — do not delete anything
4. Under GDPR, a breach must be reported to the supervisory authority within **72 hours** of discovery
5. Affected customers must be notified if the breach is likely to result in high risk to their rights

---

## Prohibited Actions
- Copying customer PII to personal devices, email, or cloud storage
- Sharing customer data with third parties without a signed Data Processing Agreement
- Using production customer data in development or testing environments
- Bypassing encryption for performance reasons
- Retaining data beyond its retention period

Violations of this policy may result in disciplinary action, termination, and/or legal liability.
