# Rename this file to backend.tf ONLY AFTER the bucket has been created successfully.
terraform {
  backend "s3" {
    bucket       = "commerce-tfstate-036706657723-ap-south-1"
    key          = "bootstrap/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
