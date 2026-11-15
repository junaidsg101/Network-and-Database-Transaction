# Behavior Report
_Generated 2026-11-15 08:37:28.647_

## Fraud & timeout behavior
- Payments processed (timeout scenarios): **1**
- Released after safe retries: **1**
- Escalated to human triage (HIGH): **0**
- Risk tier distribution: {'LOW': 1}
- Mean risk score: **11.0/100**
- Transactions blocked because of a timeout alone: **0**

## Concurrent transaction behavior
- Committed writes (WAL-acknowledged): **1**
- Accounts ever below zero (overdraft / double-spend indicator): **0**
- Isolation: MVCC snapshot for reads, per-account serialization + optimistic versioning for writes.

## Audit trail
Raw events: `reports/history/events.jsonl`; application log: `logs/app.log`.
