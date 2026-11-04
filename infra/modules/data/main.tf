resource "aws_security_group" "database" {
  name        = "commerce-dev-postgres"
  description = "PostgreSQL access from EKS nodes only"
  vpc_id      = var.vpc_id
  tags        = { Name = "commerce-dev-postgres" }
}

resource "aws_vpc_security_group_ingress_rule" "database_from_nodes" {
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = var.node_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "EKS node/pod connections to PostgreSQL"
}

resource "aws_db_subnet_group" "main" {
  name       = "commerce-dev-db"
  subnet_ids = var.data_subnet_ids
}

resource "aws_db_parameter_group" "main" {
  name   = "commerce-dev-postgres17"
  family = "postgres17"
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

resource "aws_cloudwatch_log_group" "postgres" {
  name              = "/aws/rds/instance/commerce-dev-postgres/postgresql"
  retention_in_days = 7
}

resource "aws_db_instance" "main" {
  identifier                  = "commerce-dev-postgres"
  engine                      = "postgres"
  engine_version              = "17"
  instance_class              = "db.t4g.micro"
  db_name                     = "commerce"
  username                    = "commerce_admin"
  manage_master_user_password = true

  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false
  multi_az               = false
  port                   = 5432

  backup_retention_period    = 3
  backup_window              = "19:00-19:30"
  maintenance_window         = "sun:20:00-sun:20:30"
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "commerce-dev-postgres-final"
  delete_automated_backups   = true

  enabled_cloudwatch_logs_exports = ["postgresql"]
  depends_on                      = [aws_cloudwatch_log_group.postgres]
}

resource "aws_sqs_queue" "dead_letter" {
  name                      = "commerce-dev-payments-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "payments" {
  name                       = "commerce-dev-payments"
  message_retention_seconds  = 345600
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dead_letter" {
  queue_url = aws_sqs_queue.dead_letter.url
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.payments.arn]
  })
}

resource "aws_sqs_queue_policy" "tls_only" {
  for_each = {
    payments = { url = aws_sqs_queue.payments.url, arn = aws_sqs_queue.payments.arn }
    dlq      = { url = aws_sqs_queue.dead_letter.url, arn = aws_sqs_queue.dead_letter.arn }
  }
  queue_url = each.value.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "sqs:*"
      Resource  = each.value.arn
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

# Secret metadata only: actual credential values are written outside Terraform.
resource "aws_secretsmanager_secret" "application_database" {
  name                    = "commerce/dev/database"
  description             = "Restricted application DB credentials, populated by the DB bootstrap job"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "webhook" {
  name                    = "commerce/dev/webhook"
  description             = "Dummy payment callback signing key"
  recovery_window_in_days = 7
}
