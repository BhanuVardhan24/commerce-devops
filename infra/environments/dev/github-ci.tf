# Account-level provider is created/reused manually and recorded in the resource register.
data "aws_iam_openid_connect_provider" "github" {
  arn = "arn:aws:iam::036706657723:oidc-provider/token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_ecr" {
  name                 = "CommerceGithubEcrPushRole"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike   = { "token.actions.githubusercontent.com:sub" = local.github_main_subjects }
      }
    }]
  })
}

resource "aws_iam_policy" "github_ecr" {
  name = "CommerceGithubEcrPushPolicy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RegistryAuthentication"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "PublishOnlyCommerceImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
          "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"
        ]
        Resource = "arn:aws:ecr:ap-south-1:036706657723:repository/commerce/catalog"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_ecr" {
  role       = aws_iam_role.github_ecr.name
  policy_arn = aws_iam_policy.github_ecr.arn
}

output "github_ecr_push_role_arn" { value = aws_iam_role.github_ecr.arn }
