provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["036706657723"]
  default_tags {
    tags = {
      Project     = "CommerceDevOps"
      Environment = "dev"
      Owner       = "BhanuVardhan"
      ManagedBy   = "Terraform"
    }
  }
}

module "network" {
  source = "../../modules/network"
}

resource "aws_ecr_repository" "catalog" {
  name                 = "commerce/catalog"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "catalog" {
  repository = aws_ecr_repository.catalog.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire only untagged images older than 14 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 14
      }
      action = { type = "expire" }
    }]
  })
}
