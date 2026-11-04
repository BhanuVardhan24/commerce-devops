output "vpc_id" { value = aws_vpc.main.id }
output "public_subnet_ids" { value = [for s in aws_subnet.public : s.id] }
output "private_subnet_ids" { value = [for s in aws_subnet.private : s.id] }
output "data_subnet_ids" { value = [for s in aws_subnet.data : s.id] }
output "nat_gateway_id" { value = aws_nat_gateway.main.id }
output "nat_public_ip" { value = aws_eip.nat.public_ip }
