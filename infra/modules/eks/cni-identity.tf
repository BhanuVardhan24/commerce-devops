resource "aws_iam_role" "cni" {
  name = "CommerceVpcCniRole"

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
            "aws:RequestTag/kubernetes-service-account" = "aws-node"
          }

          ArnEquals = {
            "aws:SourceArn" = aws_eks_cluster.main.arn
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cni" {
  role       = aws_iam_role.cni.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}