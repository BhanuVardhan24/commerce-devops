## Inspector removed from project scope

- ECR registry restored to BASIC scanning.
- Inspector ECR scanning deactivated in ap-south-1.
- CI security gates retained: Gitleaks and Trivy.
- SonarQube quality gate remains planned.
- CommerceInspectorProvisioningPolicy: detach from CommerceDevMachineRole
  and delete after confirming deactivation.
- AWSServiceRoleForAmazonInspector2: retain unless confirmed unused
  by all other Inspector workloads.
- Inspector approval is no longer required for release candidates.

## EKS workload identity

Terraform-managed:
- Add-on: eks-pod-identity-agent on commerce-dev
- Role: CommerceExternalSecretsRole
- Inline policy: CommerceApplicationSecretsRead
- Pod Identity association:
  namespace external-secrets / service account external-secrets

Manually managed:
- Policy: CommerceWorkloadIdentityProvisioningPolicy
- Attached to: CommerceDevMachineRole

Cleanup:
- Remove dependent Helm workloads before removing their identities.
- Terraform removes the association, inline policy, role, and agent.
- Remove the provisioning policy attachment and policy afterward.

## Quality gate scope

- SonarQube and Amazon Inspector excluded from project scope.
- Automated tests, Gitleaks, and Trivy remain required.

## External Secrets Operator

- Helm release: external-secrets
- Namespace: external-secrets
- Service account: external-secrets
- Uses existing CommerceExternalSecretsRole through EKS Pod Identity.
- No new IAM roles or policies created in this step.

Application resources:
- Namespace: commerce
- SecretStore: commerce/commerce-aws
- ExternalSecret: commerce/commerce-webhook
- Generated Secret: commerce/commerce-webhook

Cleanup:
- Remove application workloads and ExternalSecrets first.
- Uninstall the external-secrets Helm release before removing its IAM identity.
- Remove remaining stores, namespaces, and unused ESO CRDs after checking dependencies.
- AWS Secrets Manager secrets remain managed by Terraform.

Operations:
- ESO refreshes the Kubernetes Secret.
- Applications consuming secrets as environment variables need a restart
  to use updated values.

  ## RDS application access

- PostgreSQL login: commerce_app
- Database: commerce
- Schema: commerce
- Application tables created by commerce_app.
- Application login has no superuser, role-management,
  database-creation, replication, or bypass-RLS privileges.
- Application login can create tables in its commerce schema.

Secrets:
- AWS secret: commerce/dev/database, Terraform-managed metadata.
- Secret value initialized outside Terraform.
- ExternalSecret: commerce/commerce-database
- Generated Kubernetes Secret: commerce/commerce-database
- Public RDS CA bundle: gitops/platform/external-secrets/rds-ca.pem

Temporary provisioning:
- Inline policy: CommerceDatabaseBootstrapPolicy
- Role: CommerceDevMachineRole
- Remove policy after successful bootstrap.
- Temporary pod: commerce/commerce-db-bootstrap
- Pod deleted after setup.

Cleanup:
- Removing the Kubernetes Secret does not remove the database login.
- Destroying the project RDS instance removes its database objects.
- Retained final snapshots also retain database data and roles.
- If retaining RDS instead, review and remove project database objects
  and login separately.

  ## Initial application Helm deployment

- Release: commerce
- Namespace: commerce
- Deployments: commerce-web, commerce-provider, commerce-worker,
  commerce-redis
- ClusterIP services: commerce-web, commerce-provider, commerce-redis
- ConfigMap: commerce-rds-ca
- Uses existing ESO-managed database and webhook Secrets.
- No new IAM roles, policies, or AWS load balancers.

Current limitations:
- Payment worker still uses PostgreSQL polling; SQS integration pending.
- Redis carts are disposable.
- Public ALB access and GitOps adoption pending.
- Initial deployment uses existing database tables.
- Blue/green delivery and automated migrations pending.

Cleanup:
- helm uninstall commerce -n commerce
- Helm uninstall does not delete RDS data or ESO-managed Secrets.