data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "zone-type"
    values = ["availability-zone"]
  }
}

locals {
  zones = {
    a = { az = sort(data.aws_availability_zones.available.names)[0], number = 0 }
    b = { az = sort(data.aws_availability_zones.available.names)[1], number = 1 }
  }
}

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "commerce-dev-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "commerce-dev-igw" }
}

resource "aws_subnet" "public" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.value.az
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, each.value.number)
  map_public_ip_on_launch = false
  tags = {
    Name                                 = "commerce-dev-public-${each.key}"
    "kubernetes.io/role/elb"             = "1"
    "kubernetes.io/cluster/commerce-dev" = "shared"
  }
}

resource "aws_subnet" "private" {
  for_each          = local.zones
  vpc_id            = aws_vpc.main.id
  availability_zone = each.value.az
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, 10 + each.value.number)
  tags = {
    Name                                 = "commerce-dev-private-${each.key}"
    "kubernetes.io/role/internal-elb"    = "1"
    "kubernetes.io/cluster/commerce-dev" = "shared"
  }
}

resource "aws_subnet" "data" {
  for_each          = local.zones
  vpc_id            = aws_vpc.main.id
  availability_zone = each.value.az
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, 20 + each.value.number)
  tags              = { Name = "commerce-dev-data-${each.key}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "commerce-dev-public-rt" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "commerce-dev-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["a"].id
  depends_on    = [aws_internet_gateway.main]
  tags          = { Name = "commerce-dev-nat" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "commerce-dev-private-rt" }
}

resource "aws_route" "private_outbound" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "commerce-dev-isolated-data-rt" }
}

resource "aws_route_table_association" "data" {
  for_each       = aws_subnet.data
  subnet_id      = each.value.id
  route_table_id = aws_route_table.data.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-south-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  tags              = { Name = "commerce-dev-s3-endpoint" }
}
