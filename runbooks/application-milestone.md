# Local application milestone

## Scope
Small catalog/storefront, Redis carts, PostgreSQL order snapshots, durable payment jobs,
separate mock provider, signed callbacks, retrying worker and HTTP acceptance tests.
The product catalog remains a tiny code fixture to keep application work bounded.

## Flow
Browser -> Redis cart -> order API -> PostgreSQL order + job in one transaction ->
worker -> mock provider -> signed webhook -> final order status.

## Why these files exist
- app/data.py: shared connections, catalog fixtures and additive schema initialization.
- app/main.py: existing catalog/HTML plus cart, checkout, order status and webhook routes.
- app/provider.py: mock external provider with durable idempotency records.
- app/worker.py: local PostgreSQL job transport; bounded retries and DEAD status.
- app/templates/index.html: minimal customer journey and payment outcome controls.
- scripts/checkout_test.py: simultaneous duplicate checkout, decline, lost-response retry,
  request-key conflict and unsigned-webhook rejection.
- compose.yaml: one shared image, explicit dependency health and schema job.
- .github/workflows/ci.yml: complete workflow, including packaged and end-to-end tests.

## Important syntax
- `with db() as conn`: commit on successful completion; roll back on an exception.
- SQL `%s` with a separate parameter tuple: bind values without building SQL strings.
- `pg_advisory_xact_lock`: serialize concurrent requests with the same checkout key.
- UNIQUE/PRIMARY KEY: enforce uniqueness even if requests race.
- `FOR UPDATE ... SKIP LOCKED`: reserve a pending job while other workers skip it.
- HMAC and compare_digest: validate the callback's shared-secret signature.
- YAML `&app` and `<<: *app`: reuse common service settings across the same image.
- `service_completed_successfully`: start application components after migration succeeds.

## Failure behavior
- Identical checkout keys return the existing order; changed cart identity/mode returns 409.
- Checkout captures current server-side prices; browser totals are not accepted.
- Order + job commit atomically; an unavailable worker leaves recoverable pending work.
- Provider keys are order IDs; repeated calls reuse the original payment result.
- timeout_once commits a provider result and delivers its callback, then returns 503 once.
  This models an ambiguous/lost response after the operation took effect. The next call
  uses the same key; it does not create a second payment.
- Repeated callbacks have a stable event ID; conflicting terminal outcomes are rejected.
- After five failed deliveries, a job becomes DEAD for operator inspection. It does not
  automatically label a possibly successful payment as declined.

## Local queue limitation
This is explicitly PostgreSQL polling, not SQS. During AWS provisioning, the durable job
record becomes the outbox source for SQS publication, and the worker will consume SQS.
Do not claim SQS, EKS, payment compliance or production readiness from this local stage.

## Operator commands
Start: docker compose up --build --wait --wait-timeout 120
Check: docker compose ps --all
Logs: docker compose logs --tail 100 worker provider web
HTTP acceptance: python3 scripts/checkout_test.py
Stop while preserving data: docker compose down

Inspect jobs:
docker compose exec -T postgres psql -U commerce -d commerce -c "SELECT * FROM payment_jobs;"

After investigating/fixing a DEAD job, replay ONE known synthetic order:
docker compose exec -T postgres psql -U commerce -d commerce -c "UPDATE payment_jobs SET state='PENDING', attempts=0, available_at=now() WHERE order_id='REPLACE_ORDER_ID' AND state='DEAD';"

## Lab boundaries and next DevOps stages
No customer authentication; random cart/order IDs are not an authorization system.
Provider has no host-published port; app's local port binds to loopback only.
Web/worker/provider share the local bootstrap database identity for now. AWS deployment
must split least-privilege database/workload identities and move dummy shared secrets into
Secrets Manager/ESO. Provider and app share one database here only to keep the lab small.
Before public ALB exposure, add the lab access boundary and narrow ingress routing.

No new AWS roles, policies or resources are created by this local milestone.
The entire agreed DevOps stack remains required in subsequent infrastructure, security,
GitOps, observability and recovery stages.
