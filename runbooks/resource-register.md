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