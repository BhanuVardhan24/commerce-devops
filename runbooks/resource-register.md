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