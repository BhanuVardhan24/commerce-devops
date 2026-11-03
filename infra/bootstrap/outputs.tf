output "state_bucket_name" {
  description = "Dedicated state bucket; remove only after all dependent infrastructure."
  value       = aws_s3_bucket.state.id
}

output "bootstrap_state_key" {
  value = "bootstrap/terraform.tfstate"
}
