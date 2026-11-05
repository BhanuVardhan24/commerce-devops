resource "aws_cloudwatch_log_group" "commerce_app" {
  name              = "/aws/eks/commerce-dev/commerce"
  retention_in_days = 7
}

resource "aws_iam_role" "fluent_bit" {
  name = "CommerceFluentBitRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:SourceAccount"                         = "036706657723"
          "aws:RequestTag/kubernetes-namespace"       = "monitoring"
          "aws:RequestTag/kubernetes-service-account" = "commerce-fluent-bit"
        }
        ArnEquals = {
          "aws:SourceArn" = "arn:aws:eks:ap-south-1:036706657723:cluster/commerce-dev"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "fluent_bit" {
  name = "CommerceCloudWatchLogWrite"
  role = aws_iam_role.fluent_bit.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.commerce_app.arn}:log-stream:*"
      },
      {
        Effect   = "Allow"
        Action   = "logs:DescribeLogStreams"
        Resource = aws_cloudwatch_log_group.commerce_app.arn
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "fluent_bit" {
  cluster_name    = module.eks.cluster_name
  namespace       = "monitoring"
  service_account = "commerce-fluent-bit"
  role_arn        = aws_iam_role.fluent_bit.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy.fluent_bit
  ]
}

resource "aws_cloudwatch_metric_alarm" "payments_backlog" {
  alarm_name          = "commerce-dev-payments-backlog-age"
  alarm_description   = "A visible payment message has been waiting for at least 120 seconds."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 120
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = "commerce-dev-payments"
  }
}

resource "aws_cloudwatch_metric_alarm" "payments_dlq" {
  alarm_name          = "commerce-dev-payments-dlq-visible"
  alarm_description   = "At least one payment message is visible in the dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = "commerce-dev-payments-dlq"
  }
}