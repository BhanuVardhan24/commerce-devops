terraform {
  required_version = "= 1.17.1"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.0"
    }
  }
  backend "s3" {
    bucket       = "commerce-tfstate-036706657723-ap-south-1"
    key          = "commerce/dev/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
