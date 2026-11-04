# Project Resource and Teardown Register

Update this file whenever a project resource, role, policy or attachment is created.
Record exact names and ownership before proceeding to the next stage.

## IAM resources

| Type | Name | Ownership | Status |
|---|---|---|---|
| IAM role | CommerceDevMachineRole | Manual bootstrap | Attached to development EC2 |
| Instance profile | Confirm exact name in Console | Manual bootstrap | Associated with development EC2 |
| Project-created managed policies | None yet | Not applicable | Not created |
| Inline policies | None yet | Not applicable | Not created |

For each future policy, record:
- Policy name and ARN, or inline policy name and parent role.
- Roles or other identities to which it is attached.
- Whether Terraform or manual bootstrap owns it.
- The resources that still depend on it.

## Existing workstation resources

| Type | Identifier | Ownership |
|---|---|---|
| EC2 instance | i-04b335b1a411fb2b7 | User-created |
| EBS volume | vol-0932f0a24878d52af | User-created |
| Elastic IP | 13.202.177.91 | User-created |
| EIP association | eipassoc-0bf41932f7b601896 | User-created |

Region: ap-south-1.

## Final cleanup rules

1. Keep the workstation role until application infrastructure teardown finishes.
2. Remove project policy attachments before deleting project-created policies.
3. Remove inline policies before deleting their roles.
4. Detach instance profiles from EC2 before removing their roles/profiles.
5. Never delete AWS-managed policies; remove only project attachments.
6. Confirm whether the development workstation should be retained.
7. Account for retained disks, snapshots and Elastic IPs separately.
8. Verify actual resource inventory after Terraform destroy.

## Local Docker storage

| Resource | Purpose | Cleanup |
|---|---|---|
| commerce-devops_postgres_data | Local PostgreSQL data | Retain between development sessions; remove only when lab data is no longer needed |

Redis currently has persistence disabled and no named data volume.

Local PostgreSQL storage is not an AWS RDS resource.
No additional IAM roles or policies were created in this stage.

## Terraform foundation

| Resource | Name | Ownership |
|---|---|---|
| Customer-managed IAM policy | CommerceTerraformStateBootstrapPolicy | Manual bootstrap |
| Policy attachment | CommerceDevMachineRole → CommerceTerraformStateBootstrapPolicy | Manual bootstrap |
| S3 state bucket | commerce-tfstate-036706657723-ap-south-1 | Terraform: infra/bootstrap |
| Bucket protections | Versioning, encryption, public-access block, TLS policy | Terraform: infra/bootstrap |
| Bootstrap state | bootstrap/terraform.tfstate and object versions | Terraform backend |

Policy ARN:
arn:aws:iam::036706657723:policy/CommerceTerraformStateBootstrapPolicy

No new IAM role or instance profile created.

Destroy application infrastructure before removing this foundation.
Migrate bootstrap state back to local before final bucket deletion.
Remove bucket protection deliberately during reviewed final cleanup.
Detach/delete the custom policy only after state cleanup finishes.

## Network and ECR

- Custom policy: CommerceNetworkEcrProvisioningPolicy
- Attachment: CommerceDevMachineRole → CommerceNetworkEcrProvisioningPolicy
- VPC: commerce-dev-vpc
- Six subnets, Internet Gateway, route tables and routes
- NAT gateway: commerce-dev-nat
- New Elastic IP: commerce-dev-nat-eip
- S3 gateway endpoint: commerce-dev-s3-endpoint
- ECR repository and lifecycle policy: commerce/catalog
- Terraform state: commerce/dev/terraform.tfstate
- Actual resource IDs: docs/evidence/network-outputs.json

Terraform owns these infrastructure resources.
The custom IAM policy and attachment are manually bootstrapped.
Destroy dependent clusters/databases/load balancers before networking.
Keep provisioning permissions until teardown finishes.

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

## GitHub image publishing

- Manual policy: CommerceCiProvisioningPolicy
- Attachment: CommerceDevMachineRole → CommerceCiProvisioningPolicy
- GitHub OIDC provider: token.actions.githubusercontent.com
  Record whether project-created or shared.
- Terraform role: CommerceGithubEcrPushRole
- Terraform policy: CommerceGithubEcrPushPolicy
- Terraform attachment: publisher policy → publisher role
- Pipeline-created ECR images: commerce/catalog
- GitHub CI evidence artifacts: ci-reports-*, seven-day retention

Disable publishing before final image cleanup.
Remove publisher resources through Terraform.
Retain a shared OIDC provider when other projects use it.
