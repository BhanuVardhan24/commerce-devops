module "data" {
  source                 = "../../modules/data"
  vpc_id                 = module.network.vpc_id
  data_subnet_ids        = module.network.data_subnet_ids
  node_security_group_id = module.eks.cluster_security_group_id
}

output "database_address" { value = module.data.database_address }
output "database_port" { value = module.data.database_port }
output "database_engine_version" { value = module.data.database_engine_version }
output "database_security_group_id" { value = module.data.database_security_group_id }
output "database_master_secret_arn" { value = module.data.database_master_secret_arn }
output "application_database_secret_arn" { value = module.data.application_database_secret_arn }
output "webhook_secret_arn" { value = module.data.webhook_secret_arn }
output "payments_queue_url" { value = module.data.payments_queue_url }
output "payments_queue_arn" { value = module.data.payments_queue_arn }
output "payments_dlq_url" { value = module.data.payments_dlq_url }
output "payments_dlq_arn" { value = module.data.payments_dlq_arn }
