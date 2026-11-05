resource "aws_iam_role" "alb_controller" {
  name = "CommerceLoadBalancerControllerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
        Condition = {
          StringEquals = {
            "aws:SourceAccount"                         = "036706657723"
            "aws:RequestTag/kubernetes-namespace"       = "kube-system"
            "aws:RequestTag/kubernetes-service-account" = "aws-load-balancer-controller"
          }
          ArnEquals = {
            "aws:SourceArn" = "arn:aws:eks:ap-south-1:036706657723:cluster/commerce-dev"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "alb_controller" {
  role = aws_iam_role.alb_controller.name

  policy_arn = "arn:aws:iam::036706657723:policy/CommerceLoadBalancerControllerPolicy"
}

resource "aws_eks_pod_identity_association" "alb_controller" {
  cluster_name    = module.eks.cluster_name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.alb_controller.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy_attachment.alb_controller
  ]
}