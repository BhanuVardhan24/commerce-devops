# Private data and queue services

## Ownership and scope
infra/modules/data defines the resources. infra/environments/dev/data-services.tf calls it
using network outputs and the EKS node security group. Everything remains in existing dev
state commerce/dev/terraform.tfstate. Initial expected additions: 13, no replacements.
Redis remains a temporary in-cluster cache to be deployed by Helm, not ElastiCache.
Application still uses local services until cloud configuration/SQS transport are deployed.

## Bootstrap permission
Create customer-managed CommerceDataProvisioningPolicy from infra/iam, attach it to existing
CommerceDevMachineRole. ARN: arn:aws:iam::036706657723:policy/CommerceDataProvisioningPolicy.
Keep the preceding policies attached. No new project IAM role in this batch.
The policy covers named RDS resources, named queues/secrets and database logs, plus regional
security-group management. It also permits limited RDS service-linked-role validation and
creation, plus encryption metadata/service grants required for encrypted RDS.
RDS-managed master-secret creation is allowed without allowing retrieval of other RDS
master passwords. A narrowly scoped bootstrap workload role will initialize the app user.

## Database
commerce-dev-postgres, PostgreSQL major 17 with managed minor updates, db.t4g.micro,
20 GiB encrypted gp3 (autoscaling ceiling 30), three-day backups, seven-day PostgreSQL log
retention, single AZ for a small lab. The subnet group contains both isolated data subnets;
that does NOT make a single-AZ instance Multi-AZ. No public address. Only TCP5432 from the
EKS cluster/node security group is allowed. SQL credentials and TLS are required in addition
to this network rule. Parameter group forces SSL.

RDS creates/rotates the master password in a service-managed secret. Terraform stores the
secret ARN, not a password value, because manage_master_user_password=true. App credentials
will be distinct; do not deploy application pods using the master account. The existing
local PostgreSQL data is not copied or migrated by this Terraform apply.

## Queues
commerce-dev-payments: standard queue, visibility60s, longpoll20s, retention4days, DLQafter5
receives. commerce-dev-payments-dlq: retention14days, accepts redrive only from source queue.
Both use SQS-managed encryption and reject insecure transport. Standard delivery can repeat;
the cloud worker must retain durable idempotency and delete only after committing results.
Database job records become the outbox for SQS publication in the delivery integration stage.

## Secret containers
commerce/dev/webhook: initialize via scripts/initialize_webhook_secret.py; script uses stdin,
does not print the key, and preserves an existing secret version on ordinary reruns. Do not
run initialization concurrently. Secret versions are outside Terraform to avoid putting
values in state. Verify metadata, never paste retrieved values into this chat or Git.
commerce/dev/database: intentionally empty until the DB bootstrap job creates a restricted
application database account. ESO/workload identity will be configured before app deployment.
Both containers have seven-day deletion recovery windows. RDS owns its master secret lifecycle.

## Apply and verify
terraform -chdir=infra/environments/dev init
terraform fmt -recursive infra
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev plan -out=data.tfplan
terraform -chdir=infra/environments/dev apply data.tfplan
python3 scripts/initialize_webhook_secret.py
python3 scripts/check_rds_network.py
python3 scripts/check_sqs.py
terraform -chdir=infra/environments/dev plan

Expected: accepting connections from an EKS check Job, SQS probe completes, no Terraform
changes. The database check verifies private reachability, not authenticated queries.
The Job is removed after checking. The SQS script should run before an application consumer
is deployed; it releases unrelated messages and deletes only its own probe.

## Console navigation (Mumbai)
- RDS -> Databases -> commerce-dev-postgres: Available; PostgreSQL17; t4g.micro.
- Connectivity & security: publicly accessible No; data subnet group; DB SG5432 source node SG.
- Configuration: encrypted storage; managed master-secret link; deletion protection.
- Maintenance & backups: three-day retention; backup windows are UTC.
- SQS -> commerce-dev-payments: visibility60, retention4days, longpoll20, DLQmaxReceiveCount5.
- SQS -> commerce-dev-payments-dlq: retention14days, restricted source queue redrive policy.
- Secrets Manager: commerce/dev/webhook has a current version; commerce/dev/database is
  metadata-only until app-user bootstrap; RDS-generated master secret is present.
- CloudWatch -> Logs -> /aws/rds/instance/commerce-dev-postgres/postgresql: seven-day retention.

## Teardown register additions
| Resource | Name | Ownership |
|---|---|---|
| Custom managed policy/attachment | CommerceDataProvisioningPolicy -> CommerceDevMachineRole | Manual bootstrap |
| RDS instance | commerce-dev-postgres | Terraform dev state |
| DB subnet/parameter groups | commerce-dev-db / commerce-dev-postgres17 | Terraform dev state |
| DB SG and ingress | commerce-dev-postgres / TCP5432 from EKS SG | Terraform dev state |
| PostgreSQL log group | /aws/rds/instance/commerce-dev-postgres/postgresql | Terraform dev state |
| Source queue / DLQ / policies | commerce-dev-payments / commerce-dev-payments-dlq | Terraform dev state |
| Secret containers | commerce/dev/database, commerce/dev/webhook | Terraform dev state |
| Webhook secret versions | generated outside Terraform | Account for during secret deletion |
| Master secret | RDS-generated ARN in outputs | RDS-managed lifecycle |
| Backups/final snapshot | automatic backups / commerce-dev-postgres-final | Inspect and remove after evidence/restore drills |

AWSServiceRoleForRDS may be created if absent. Record it, but do not automatically delete a
shared account-level service-linked role. Default aws/rds and aws/secretsmanager encryption
keys are AWS-managed, not new customer-managed KMS keys to delete.

## Final cleanup
Finish recovery evidence first. Review disabling deletion_protection through Terraform
apply before final destroy. A final snapshot is deliberately required; remove the retained
snapshot after the drill. If a snapshot with the configured final name already exists,
choose a new explicit final_snapshot_identifier before destroy. Account for automatic-backup
retention/deletion. Secret recovery windows continue after destroy and reserve their names;
inspect scheduled deletion rather than force-deleting blindly. Remove data services before
EKS/node SG/network and before the remote state. Remove the custom policy attachment/policy
versions/policy only after its resources are gone. RDS, storage, snapshots, logs and Secrets
Manager incur charges; stopping local Compose has no effect on cloud resources.
