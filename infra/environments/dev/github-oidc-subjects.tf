# Pin the observed exact subject after the first successful main-branch run.
# Wildcards below occupy immutable numeric IDs only; owner/repo/branch names are exact.
locals {
  github_main_subjects = [
    "repo:BhanuVardhan24/commerce-devops:ref:refs/heads/main",
    "repo:BhanuVardhan24@*/commerce-devops@*:ref:refs/heads/main"
  ]
}
