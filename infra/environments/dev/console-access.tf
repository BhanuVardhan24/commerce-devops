resource "aws_eks_access_entry" "console_viewer" {
  cluster_name      = module.eks.cluster_name
  principal_arn     = "arn:aws:iam::036706657723:user/Skull_User_1"
  type              = "STANDARD"
  kubernetes_groups = ["commerce-console-viewers"]
}

resource "aws_eks_access_policy_association" "console_viewer" {
  cluster_name  = module.eks.cluster_name
  principal_arn = aws_eks_access_entry.console_viewer.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }
}