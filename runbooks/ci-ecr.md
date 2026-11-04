# GitHub OIDC and candidate image publishing

## Flow
PR: Python tests -> Gitleaks full-history scan -> build/start Compose -> packaged tests ->
HTTP checks -> Trivy report/gate -> sanitized report artifact. No PR receives the AWS role.
Main push: same checks -> temporary AWS session -> tag the SAME tested local image -> ECR
push -> capture immutable repository digest and provenance in reports/release.json.
No Kubernetes/Argo deployment occurs. Image is a candidate pending SonarQube and completed
Inspector gate. Those are mandatory before GitOps promotion, not removed from the stack.

## IAM Console bootstrap
1. IAM -> Identity providers: if token.actions.githubusercontent.com exists, reuse it and
   record shared ownership. Otherwise Add provider, type OpenID Connect, URL
   https://token.actions.githubusercontent.com, audience sts.amazonaws.com. Record whether
   this project created it. IAM retrieves the certificate information; don't paste leaf hashes.
2. Create managed policy CommerceCiProvisioningPolicy from infra/iam JSON and attach it
   to CommerceDevMachineRole. Existing policies remain. This permits Terraform to read the
   provider and manage only CommerceGithubEcrPushRole, CommerceGithubEcrPushPolicy and their
   attachment. No additional privilege is given to the application or GitHub publisher.

## Terraform ownership
dev/github-ci.tf creates a dedicated role, customer-managed ECR push policy and attachment
(three additions). GitHub's role is NOT the workstation's powerful provisioning role.
ecr:GetAuthorizationToken requires Resource *. Actual layer upload/push/read permissions
are scoped to commerce/catalog; no EKS, database, secrets, delete-image or Terraform access.

## Trust subjects and exact ID pinning
AWS trust requires audience sts.amazonaws.com and main branch of BhanuVardhan24/commerce-devops.
No workflow environment is configured. Environments would change the OIDC subject.
New GitHub repositories use owner/repository numeric IDs in their subject. Initial trust
supports legacy exact names and an immutable-format pattern with wildcards ONLY in the ID
positions. Pin the exact observed subject immediately after the first successful main run:
- Download the CI artifact's oidc-subject.txt (metadata only, NOT the bearer token).
- Upload it as docs/evidence/oidc-subject.txt in the EC2 repository.
- python3 scripts/pin_github_oidc_subject.py docs/evidence/oidc-subject.txt
- Review Terraform plan: only publisher role trust should change to an exact subject.
- Apply reviewed plan and commit the pin. Do not authorize PRs, feature branches, arbitrary
  repositories or substitute repo:* patterns to work around authentication errors.

## Apply and run
terraform -chdir=infra/environments/dev init
terraform fmt -recursive infra
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev plan -out=ci-identity.tfplan
terraform -chdir=infra/environments/dev apply ci-identity.tfplan
Push feature branch and open PR. Security checks must pass before merge. After merge, main
publishes a candidate; PR does not publish. No AWS access-key GitHub secret is required.

## Gate policy
Gitleaks8.30.1: any committed-secret finding fails CI; JSON/log findings redacted.
Trivy0.76.1: save ALL image vulnerability findings, block fixable HIGH/CRITICAL. Unfixed
findings remain visible for review; no blanket .trivyignore entries are introduced. Fix the
dependency/base package instead of lowering the gate. A finding report is not a complete
deployment approval; SonarQube and Inspector remain pending. Tool archives are version-pinned
and checked against official release checksums. Actions are pinned to commit SHAs.
Python image advances within3.14 from3.14.4 to3.14.10; app dependencies stay locked in the
existing requirements.txt. No backend features change in this stage.

## Artifact and immutable tag
Tag: sha-<source SHA>-run-<run ID>-<attempt>. Run/attempt suffix permits retries while keeping
ECR tags immutable. Never rebuild after tests to publish. release.json records source,
run URL, config image ID, ECR digest, actual OIDC subject and pending approval status.
Artifacts contain no AWS credentials or raw OIDC token. Retention seven days. Full Git
history scanning can surface old leaks: remove/rotate actual credentials and resolve the
history/finding, not just hide the latest occurrence. reports/ should remain uncommitted.

## Console checks
IAM -> Identity providers: GitHub URL and audience.
IAM -> Roles -> CommerceGithubEcrPushRole: trust main only; CommerceGithubEcrPushPolicy attached.
GitHub -> PR -> Checks: application and container/security jobs pass; AWS steps skipped.
GitHub -> Actions -> successful MAIN Application CI -> Summary/Artifacts: candidate digest,
ci-reports download, Gitleaks/Trivy/test results, release.json and oidc-subject.txt.
ECR -> Private repositories -> commerce/catalog -> Images: new immutable SHA/run tag and
matching digest. Basic scan-on-push results are not the completed enhanced Inspector gate.

## Teardown register
| Type | Name | Owner / final handling |
|---|---|---|
| Bootstrap custom policy + attachment | CommerceCiProvisioningPolicy -> CommerceDevMachineRole | Manual; remove after publisher resources are destroyed |
| OIDC provider | token.actions.githubusercontent.com | Manual/shared; delete only if project-created and no other roles use it |
| Publisher role | CommerceGithubEcrPushRole | Terraform dev state |
| Publisher custom policy | CommerceGithubEcrPushPolicy | Terraform dev state; includes policy versions |
| Publisher attachment | CommerceGithubEcrPushRole -> CommerceGithubEcrPushPolicy | Terraform dev state |
| Image candidates | commerce/catalog SHA/run tags/digests | Pipeline-created; inventory and deliberately purge at teardown |
| CI artifacts | ci-reports-* | GitHub seven-day retention; export sanitized showcase evidence |

Disable publishing workflows before final repository purge so new commits cannot recreate
images. Destroy publisher role/policy through Terraform; then remove bootstrap permissions.
Keep an account-shared provider if other roles use it. Do not delete it before role cleanup.
