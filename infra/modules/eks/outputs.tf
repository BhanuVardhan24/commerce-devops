output "cluster_name" { value = aws_eks_cluster.main.name }
output "cluster_endpoint" { value = aws_eks_cluster.main.endpoint }
output "cluster_security_group_id" { value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id }
output "node_role_arn" { value = aws_iam_role.nodes.arn }
output "cluster_role_arn" { value = aws_iam_role.cluster.arn }
output "addon_versions" { value = { for name, addon in aws_eks_addon.core : name => addon.addon_version } }
