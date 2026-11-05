locals {
  cluster_name = "commerce-dev"

  node_policies = {
    worker = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
    pull   = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
  }

  addons = toset(["vpc-cni", "coredns", "kube-proxy"])
}

resource "aws_iam_role" "cluster" {
  name = "CommerceEksClusterRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role" "nodes" {
  name = "CommerceEksNodeRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "nodes" {
  for_each   = local.node_policies
  role       = aws_iam_role.nodes.name
  policy_arn = each.value
}

resource "aws_cloudwatch_log_group" "cluster" {
  name              = "/aws/eks/${local.cluster_name}/cluster"
  retention_in_days = 7
}

resource "aws_eks_cluster" "main" {
  name     = local.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = "1.35"

  bootstrap_self_managed_addons = true

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }

  upgrade_policy {
    support_type = "STANDARD"
  }

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = [var.admin_cidr]
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_cloudwatch_log_group.cluster
  ]
}

resource "aws_eks_access_entry" "workstation" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.admin_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "workstation" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.workstation.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
}

resource "aws_launch_template" "nodes" {
  name_prefix = "commerce-dev-nodes-"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name      = "commerce-dev-worker"
      Project   = "CommerceDevOps"
      ManagedBy = "EKSManagedNodeGroup"
    }
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "commerce-dev-workers"
  node_role_arn   = aws_iam_role.nodes.arn
  subnet_ids      = var.private_subnet_ids
  instance_types  = ["t3.medium"]
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  version         = "1.35"

  scaling_config {
    min_size     = 2
    desired_size = 2
    max_size     = 3
  }

  update_config {
    max_unavailable = 1
  }

  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }

  depends_on = [
    aws_iam_role_policy_attachment.nodes
  ]
}

data "aws_eks_addon_version" "compatible" {
  for_each           = local.addons
  addon_name         = each.key
  kubernetes_version = "1.35"
  most_recent        = true
}

resource "aws_eks_addon" "core" {
  for_each     = local.addons
  cluster_name = aws_eks_cluster.main.name
  addon_name   = each.key

  addon_version = lookup(
    var.addon_pins,
    each.key,
    data.aws_eks_addon_version.compatible[each.key].version
  )

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  depends_on = [
    aws_eks_node_group.main,
    aws_iam_role_policy_attachment.cni
  ]

  dynamic "pod_identity_association" {
    for_each = each.key == "vpc-cni" ? [1] : []

    content {
      service_account = "aws-node"
      role_arn        = aws_iam_role.cni.arn
    }
  }
}