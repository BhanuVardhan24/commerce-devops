resource "aws_iam_role" "payments" {
  name = "CommercePaymentsRole"

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
            "aws:RequestTag/kubernetes-namespace"       = "commerce"
            "aws:RequestTag/kubernetes-service-account" = "commerce-payments"
          }
          ArnEquals = {
            "aws:SourceArn" = "arn:aws:eks:ap-south-1:036706657723:cluster/commerce-dev"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "payments" {
  name = "CommercePaymentsQueueAccess"
  role = aws_iam_role.payments.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = module.data.payments_queue_arn
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "payments" {
  cluster_name    = module.eks.cluster_name
  namespace       = "commerce"
  service_account = "commerce-payments"
  role_arn        = aws_iam_role.payments.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy.payments
  ]
}