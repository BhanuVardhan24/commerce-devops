# Terraform foundation

## Purpose and ownership
Pinned Terraform 1.17.1, AWS provider 6.69.0. Bootstrap resources are separate from the
future application infrastructure. All AWS calls use the existing EC2 role credentials.
No access keys are stored in Terraform or the backend configuration.

## IAM bootstrap (administrator in Console)
Create the customer-managed policy CommerceTerraformStateBootstrapPolicy from
infra/iam/CommerceTerraformStateBootstrapPolicy.json and attach it only to
CommerceDevMachineRole. This grants all S3 actions, but only on the one dedicated bucket
and its objects. It grants no VPC, EKS, RDS or IAM administration permissions.
It intentionally includes bucket/object deletion for controlled final teardown.

Policy ARN: arn:aws:iam::036706657723:policy/CommerceTerraformStateBootstrapPolicy
Role: CommerceDevMachineRole (existing)
New IAM roles: none. New instance profiles: none. New inline policies: none.
Record the actual policy ARN if a non-default IAM path is used.

## Install
ansible-playbook -i ansible/inventory.ini ansible/terraform.yml
terraform version
aws sts get-caller-identity --no-cli-pager

## Create with local state first
Keep backend.tf.example under its example extension until AFTER a successful apply.
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap fmt
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan
Review: five resources added, no unrelated changes, expected account/region/bucket.
terraform -chdir=infra/bootstrap apply bootstrap.tfplan

If the globally unique bucket name is unavailable, stop and choose a new name consistently
in main.tf, backend example and IAM policy. Never import or reuse an unfamiliar bucket.

## Migrate bootstrap state
Rename backend.tf.example to backend.tf in VS Code after creation succeeds.
terraform -chdir=infra/bootstrap init -migrate-state
Answer yes to copy the existing state into S3.
terraform -chdir=infra/bootstrap state list
terraform -chdir=infra/bootstrap plan
Expected: five managed resources and no changes.

S3 locking uses the temporary object bootstrap/terraform.tfstate.tflock. Its absence after
a completed command is expected. Do not manually delete an active lock to bypass locking.
The S3 backend uses native lockfiles; no DynamoDB table is created.

Future application infrastructure must use its OWN state key, commerce/dev/terraform.tfstate.
Do not point two different Terraform roots at the same key.

## Console verification
S3 -> Buckets -> commerce-tfstate-036706657723-ap-south-1:
- Properties: region ap-south-1, Bucket Versioning Enabled, SSE-S3 encryption.
- Permissions: all four Block Public Access settings enabled; TLS-deny bucket policy.
- Objects: bootstrap/terraform.tfstate exists after migration.
- Management/Properties tags: Project CommerceDevOps and ManagedBy Terraform.
IAM -> Policies -> CommerceTerraformStateBootstrapPolicy -> Policy usage:
CommerceDevMachineRole is attached.

## Git rules
Commit .tf, policy JSON, playbooks, backend configuration (no credentials), runbooks and
.terraform.lock.hcl. Ignore .terraform/, *.tfstate*, *.tfplan and crash logs. Treat local state
and plans as sensitive; versioned state in S3 can contain secret values in later stages.

The new Terraform validation workflow installs the same CLI with a checksum check, runs
fmt, initializes providers with -backend=false and -lockfile=readonly, and validates.
It needs no AWS credentials and does not plan or apply infrastructure. Commit the generated
infra/bootstrap/.terraform.lock.hcl before pushing, otherwise its readonly initialization fails.

## Teardown register additions
| Type | Name | Owner | Final action |
|---|---|---|---|
| Customer-managed IAM policy | CommerceTerraformStateBootstrapPolicy | Manual bootstrap | Keep until state cleanup; detach from role, delete non-default policy versions, delete policy |
| IAM attachment | CommerceDevMachineRole -> CommerceTerraformStateBootstrapPolicy | Manual bootstrap | Remove after dependent infrastructure/state cleanup |
| S3 bucket | commerce-tfstate-036706657723-ap-south-1 | Terraform infra/bootstrap | Destroy last after safe state migration and version cleanup |
| Bucket versioning, SSE-S3, public access block, TLS policy | Same bucket | Terraform infra/bootstrap | Managed with the bucket |
| State objects/versions and lockfile versions | bootstrap/terraform.tfstate and later project keys | Terraform backend | Inventory and securely remove only after dependent stacks are gone |

## Final teardown sequence (reference, not an instruction to run now)
1. Destroy application stacks while their state bucket and workstation permissions still exist.
2. Account for controller-created resources, retained data, backups, and other regions.
3. Securely pull a bootstrap-state backup outside Git. Change the bootstrap backend to local
   and migrate state back while the S3 bucket is still accessible. Verify the local state.
4. Remove prevent_destroy only for the reviewed final cleanup. Securely remove all remaining
   object versions/delete markers after confirming no other stack uses the bucket.
5. Review and apply the bootstrap destroy plan from LOCAL state.
6. Remove the manual IAM policy attachment, non-default policy versions and policy.
7. Remove the workstation role/profile only after all other teardown work finishes.

Do not destroy the bucket holding an active backend, use force_destroy during routine work,
commit state backups, or delete AWS-managed policies. S3 storage/requests accrue small charges.
