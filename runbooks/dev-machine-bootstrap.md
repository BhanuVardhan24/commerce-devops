# Development Machine Bootstrap

## Purpose

Prepare an EC2 development workstation for the commerce DevOps lab.

## Environment

- Operating system: Ubuntu
- Architecture: x86_64
- Python: 3.14.4
- AWS region: ap-south-1
- AWS CLI: version 2

## Authentication

The workstation uses an EC2 IAM role named CommerceDevMachineRole.

AWS CLI obtains temporary credentials from the attached instance profile.
Long-lived AWS access keys are not required.

The initial role has no application infrastructure permissions.
Required permissions will be added with the corresponding infrastructure stage.

## Verification

Run:

    aws --version
    aws configure get region
    aws sts get-caller-identity --no-cli-pager

Expected region: ap-south-1

Expected identity:
An assumed-role ARN containing CommerceDevMachineRole.

## Ownership

The workstation and its initial IAM role are bootstrap resources configured
outside Terraform at this stage.

They must not be assumed to belong to later application Terraform state.