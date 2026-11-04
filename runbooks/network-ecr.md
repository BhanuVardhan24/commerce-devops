# Network and ECR milestone

## Design
New dedicated VPC 10.20.0.0/16, separate from workstation VPC. Two available AZs selected
by discovery, with two public /24 subnets, two private node /24 subnets and two isolated
data /24 subnets. Public default route points to IGW, private default route to one NAT,
and data subnets have no Internet default route. DNS is enabled. ALB discovery tags are
on public/private node subnets, not data subnets. One S3 gateway endpoint serves private
node subnets. No cluster, database, ALB or new instance is created in this batch.

One NAT is a deliberate lab compromise, not multi-AZ resilient egress: both AZs depend on
the NAT AZ and cross-AZ traffic may accrue additional charges. NAT and its public IPv4
are billable while provisioned even when your local Compose stack is down.

ECR commerce/catalog stores the shared application image used by web, worker and provider.
Tags are immutable. Basic scan-on-push is an initial setting; enhanced Inspector checks
and their policy are a later security stage. Only untagged images expire after 14 days.
Keep tagged rollback artifacts. force_delete=false prevents silently purging a repository.

## IAM console step
Create customer-managed CommerceNetworkEcrProvisioningPolicy from the JSON under infra/iam;
attach to the existing CommerceDevMachineRole, preserving the state bootstrap policy.
ARN: arn:aws:iam::036706657723:policy/CommerceNetworkEcrProvisioningPolicy
Network operations are restricted by API and region, but Resource * is broad within Mumbai;
this is a workstation provisioning policy, not an application or GitHub runtime identity.
It does not grant instance launch, EKS, RDS, or IAM administration.
ECR permissions are limited to the exact repository and do not include image-push rights.

## Apply
terraform -chdir=infra/environments/dev init
terraform fmt -recursive infra
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev plan -out=network.tfplan
Expected initial count: 24 additions, no changes or destroys. Inspect exact resources.
terraform -chdir=infra/environments/dev apply network.tfplan
terraform -chdir=infra/environments/dev output
terraform -chdir=infra/environments/dev plan

Do not run from infra/bootstrap or change its state key. This root uses
commerce/dev/terraform.tfstate in the same bucket. Commit the new lock file too.

## Console verification (Mumbai)
- VPC -> Your VPCs -> commerce-dev-vpc: CIDR 10.20.0.0/16, DNS settings enabled.
- VPC -> Subnets, filter new VPC: six subnets spread over two AZs.
- VPC -> Route tables, filter new VPC: public default -> IGW, private default -> NAT,
  isolated-data table has no default route. Private route table includes S3 prefix-list route.
- VPC -> NAT gateways -> commerce-dev-nat: Available, in public-a subnet.
- VPC -> Elastic IPs: commerce-dev-nat-eip is NEW; workstation EIP 13.202.177.91 unchanged.
- VPC -> Endpoints -> commerce-dev-s3-endpoint: Gateway type and Available.
- ECR -> Private registry -> Repositories -> commerce/catalog: Immutable tags, scan-on-push,
  lifecycle rule for untagged images. Images list is empty until publishing stage.
- S3 state bucket -> Objects -> commerce/dev/terraform.tfstate: exists.

## Teardown register additions
| Resource | Identifier/name | Ownership |
|---|---|---|
| Custom IAM policy | CommerceNetworkEcrProvisioningPolicy | Manual bootstrap |
| Policy attachment | CommerceDevMachineRole -> CommerceNetworkEcrProvisioningPolicy | Manual bootstrap |
| VPC and child networking | commerce-dev-vpc / 10.20.0.0/16 | Terraform dev state |
| NAT + new EIP | commerce-dev-nat / commerce-dev-nat-eip | Terraform dev state |
| S3 gateway endpoint | commerce-dev-s3-endpoint | Terraform dev state |
| ECR repository + lifecycle rule | commerce/catalog | Terraform dev state |

Save actual IDs with terraform output, then update the main resource register.
Do not remove this network while dependent EKS/RDS/ALB resources exist. Remove ALB/ENI
dependencies first, review repository images before explicit purge, then destroy the dev
stack. Release the Terraform-managed NAT EIP; do not confuse it with the workstation EIP.
Detach/delete this custom policy only after its dependent resources are cleaned up.
