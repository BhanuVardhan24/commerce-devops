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