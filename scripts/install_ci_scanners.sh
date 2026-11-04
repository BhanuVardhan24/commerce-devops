#!/usr/bin/env bash
set -euo pipefail

GITLEAKS_VERSION=8.30.1
TRIVY_VERSION=0.76.1
tool_dir="${RUNNER_TEMP:?Run this installer in GitHub Actions}/commerce-scanners"
mkdir -p "$tool_dir"
cd "$tool_dir"

curl --fail --show-error --location --retry 3 \
  --output "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
  "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
echo "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" | sha256sum --check -
tar -xzf "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" gitleaks

curl --fail --show-error --location --retry 3 \
  --output "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
  "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
echo "c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0  trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" | sha256sum --check -
tar -xzf "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" trivy
chmod 0755 gitleaks trivy
echo "$tool_dir" >> "$GITHUB_PATH"
