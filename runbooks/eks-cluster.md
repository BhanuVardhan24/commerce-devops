# EKS cluster milestone

## Design
Cluster commerce-dev, Kubernetes 1.35, private endpoint for nodes and a public endpoint
restricted to workstation EIP 13.202.177.91/32. The public endpoint is the Kubernetes
management API, not a public application endpoint. IAM authentication and an EKS access
entry authorize the workstation role. The laptop reaches the workstation over SSH.

Two ON_DEMAND t3.medium managed nodes in existing private subnets, with encrypted 20 GiB
gp3 root volumes, IMDSv2 required, no SSH key, no public node IPv4. Min/desired/max 2/2/3;
the maximum is a limit and does NOT install or enable automatic node autoscaling.
Seven-day control-plane log retention. All three core add-ons are adopted as managed
add-ons after node bootstrap. First apply discovers compatible versions; pin them with the
provided script immediately afterwards. Kubernetes version has STANDARD support policy;
AWS automatically upgrades it when standard support expires instead of extending support.

## Preflight
The cluster, nodes, volumes and logs are billable. Check EC2 -> Service Quotas in Mumbai:
the initial nodes require four additional standard on-demand vCPUs. Including the current
two-vCPU workstation, that is at least six total if no other standard instances exist.
Allow eight if scaling to three nodes. Resolve insufficient quotas before creating the cluster.

Confirm the existing workstation still has public IPv4 13.202.177.91 before applying. The
NAT EIP 13.234.84.196 is NOT the workstation address. Do not replace the API allowlist with
0.0.0.0/0 if connection troubleshooting is needed.

## IAM bootstrap
Create customer-managed CommerceEksProvisioningPolicy from infra/iam and attach it to
CommerceDevMachineRole alongside both previous policies. The new policy scopes EKS to
commerce-dev, IAM management to exactly two project roles, attachments to four AWS-managed
policies, PassRole to EKS/EC2, and logging to the cluster log group. Launch-template APIs
are region-restricted but broad within Mumbai. The custom launch template also requires
caller RunInstances permission for managed-node creation; this is region-restricted and
limited to t3.medium when the instance-type condition is present. Service-linked role creation is restricted
to the required EKS/node-group/Auto Scaling services.

## Terraform apply
terraform -chdir=infra/environments/dev init
terraform fmt -recursive infra
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev plan -out=eks.tfplan
Expected initial change: 15 additions, no changes or destroys of existing network/ECR.
terraform -chdir=infra/environments/dev apply eks.tfplan
This commonly takes many minutes; do not interrupt a healthy create operation.

## Pin installed add-ons
python3 scripts/pin_eks_addons.py
terraform -chdir=infra/environments/dev plan
Expected: no changes. Commit the updated eks-addon-pins.tf, which contains versions only.
The version data source is discovery for the first deployment; resource versions remain
pinned after the map is saved. Later upgrades require reviewed edits to the pins.

## Install and connect
ansible-playbook -i ansible/inventory.ini ansible/kubectl.yml
kubectl version --client
aws eks update-kubeconfig --name commerce-dev --region ap-south-1 --alias commerce-dev
kubectl get nodes -o wide
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get pods -n kube-system
kubectl -n kube-system rollout status deployment/coredns --timeout=180s

Do not use sudo for kubectl, aws or Terraform. Kubeconfig is local user configuration and
must not be committed. kubectl uses the existing role through AWS CLI token generation.

## Console verification
EKS -> Clusters -> commerce-dev:
- Overview: ACTIVE, Kubernetes 1.35.
- Networking: existing vpc-0a1302f9a61ca4cbd, existing private subnets, private access enabled,
  public allowlist 13.202.177.91/32 only.
- Compute -> commerce-dev-workers: ACTIVE, desired size 2, private node instances.
- Add-ons: vpc-cni, coredns, kube-proxy ACTIVE.
- Access: CommerceDevMachineRole entry with AmazonEKSClusterAdminPolicy association.
EC2 -> Instances, filter commerce-dev-worker: two nodes, private IPs, no public IPv4.
IAM -> Roles: CommerceEksClusterRole and CommerceEksNodeRole with attachments below.
CloudWatch -> Logs -> Log groups -> /aws/eks/commerce-dev/cluster: retention seven days.
The browser Console principal may not have Kubernetes authorization: use workstation
kubectl to inspect Kubernetes resources, rather than broadening cluster access blindly.

## IAM/resource teardown register
| Resource | Name | Owner / action |
|---|---|---|
| Custom policy | CommerceEksProvisioningPolicy | Manual; remove attachment and policy versions/policy after cluster teardown |
| Attachment | CommerceDevMachineRole -> CommerceEksProvisioningPolicy | Manual |
| Role | CommerceEksClusterRole | Terraform module.eks; detach managed policy then delete after cluster |
| AWS-managed attachment | AmazonEKSClusterPolicy -> cluster role | Terraform; detach, never delete AWS policy |
| Role | CommerceEksNodeRole | Terraform module.eks; delete after node group/profile dependencies |
| AWS-managed attachments | AmazonEKSWorkerNodePolicy, AmazonEC2ContainerRegistryPullOnly, AmazonEKS_CNI_Policy -> node role | Terraform; detach, never delete AWS policies |
| Cluster / node group | commerce-dev / commerce-dev-workers | Terraform dev state |
| Launch template | commerce-dev-nodes-* | Terraform dev state |
| Access entry + policy association | CommerceDevMachineRole / AmazonEKSClusterAdminPolicy | Terraform; association is EKS access policy, not an IAM policy attachment |
| Log group | /aws/eks/commerce-dev/cluster | Terraform dev state |
| Managed add-ons | vpc-cni, coredns, kube-proxy | Terraform dev state |
| Node instances, root volumes, ASG, instance profile, cluster SG/ENIs | Generated by EKS | Inventory after node/cluster deletion; managed service normally removes its resources |

AWS may create AWSServiceRoleForAmazonEKS, AWSServiceRoleForAmazonEKSNodegroup and
AWSServiceRoleForAutoScaling if absent. These are account-level service-linked roles;
record creation, but do not automatically delete shared service-linked roles at project end.

## Identity follow-up before application deployment
For the initial bootstrap, CNI permissions are on the node role. Move them to a dedicated
aws-node workload role during the workload-identity stage, as AWS recommends. Application
pods must receive their own scoped identity for SQS/Secrets Manager rather than node-role
permissions. The existing workstation role is intentionally the cluster administrator for
this lab; CI will get a separate restricted identity and GitOps owns app delivery.

## Teardown order
Remove GitOps workloads, Ingress/ALB, PVC/CSI resources and other controller dependents
first. Remove add-ons/controllers only after dependents are gone. Then destroy node group,
cluster, roles/log group and finally networking. Do not terminate nodes manually or stop the
workstation as a substitute for deleting EKS: the control plane and managed groups persist.
