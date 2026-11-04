# Infrastructure layout and state ownership

## Two independent root stacks
- infra/bootstrap: state bucket and its protections, using bootstrap/terraform.tfstate.
- infra/environments/dev: network, ECR and the growing application platform, using
  commerce/dev/terraform.tfstate. Now calls network and eks child modules.

## Other folders
- infra/modules/network: reusable VPC/subnet/routing/NAT/S3-endpoint code. It creates
  resources only when called by dev. Its objects live in DEV state, not a module state.
- infra/modules/eks: reusable EKS, node roles, node group, access and add-on code. Called
  by dev and also stored in DEV state.
- infra/iam: JSON reference policies manually created/attached through the Console so
  Terraform can start. Merely storing JSON here does not create or track an IAM resource.

Terraform loads all .tf files in the selected directory as one configuration. File names
such as main.tf and eks.tf organize code; they do not define execution order. Resource
references and depends_on define dependencies. Terraform does not recursively load child
directories without explicit module calls.

Run bootstrap commands only for state storage. Run normal application-infrastructure
commands against infra/environments/dev. Never apply modules directly for this project.
Separate backend roots isolate state ownership/lifecycle. Individual modules inside dev
do not isolate blast radius: a dev destroy includes both network and EKS.

Bootstrap is independent because it must outlive the infrastructure whose state it stores.
The network and cluster share dev state for a manageable single-account lab. A later
production design may split these by ownership and lifecycle; that is not the current layout.
