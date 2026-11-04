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