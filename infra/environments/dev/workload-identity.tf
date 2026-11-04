resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name  = module.eks.cluster_name
  addon_name    = "eks-pod-identity-agent"
  addon_version = "v1.4.1-eksbuild.3"
}

resource "aws_iam_role" "external_secrets" {
  name = "CommerceExternalSecretsRole"

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
            "aws:RequestTag/kubernetes-namespace"       = "external-secrets"
            "aws:RequestTag/kubernetes-service-account" = "external-secrets"
          }

          ArnEquals = {
            "aws:SourceArn" = "arn:aws:eks:ap-south-1:036706657723:cluster/commerce-dev"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "external_secrets" {
  name = "CommerceApplicationSecretsRead"
  role = aws_iam_role.external_secrets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"

        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]

        Resource = [
          module.data.application_database_secret_arn,
          module.data.webhook_secret_arn
        ]
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "external_secrets" {
  cluster_name    = module.eks.cluster_name
  namespace       = "external-secrets"
  service_account = "external-secrets"
  role_arn        = aws_iam_role.external_secrets.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy.external_secrets
  ]
}

output "external_secrets_role_arn" {
  value = aws_iam_role.external_secrets.arn
}