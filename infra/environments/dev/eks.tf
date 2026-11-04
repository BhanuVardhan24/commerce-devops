module "eks" {
  source             = "../../modules/eks"
  private_subnet_ids = module.network.private_subnet_ids
  admin_role_arn     = "arn:aws:iam::036706657723:role/CommerceDevMachineRole"
  admin_cidr         = "13.202.177.91/32"
  addon_pins         = local.eks_addon_pins
  depends_on         = [module.network]
}

output "eks_cluster_name" { value = module.eks.cluster_name }
output "eks_endpoint" { value = module.eks.cluster_endpoint }
output "eks_cluster_security_group_id" { value = module.eks.cluster_security_group_id }
output "eks_cluster_role_arn" { value = module.eks.cluster_role_arn }
output "eks_node_role_arn" { value = module.eks.node_role_arn }
output "eks_addon_versions" { value = module.eks.addon_versions }
