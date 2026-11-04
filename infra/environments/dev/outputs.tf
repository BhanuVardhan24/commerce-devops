output "vpc_id" { value = module.network.vpc_id }
output "public_subnet_ids" { value = module.network.public_subnet_ids }
output "private_subnet_ids" { value = module.network.private_subnet_ids }
output "data_subnet_ids" { value = module.network.data_subnet_ids }
output "nat_gateway_id" { value = module.network.nat_gateway_id }
output "nat_public_ip" { value = module.network.nat_public_ip }
output "ecr_repository_url" { value = aws_ecr_repository.catalog.repository_url }
