#!/usr/bin/env bash
set -euo pipefail

if [[ "${GITHUB_REF:?}" != "refs/heads/main" || "${GITHUB_EVENT_NAME:?}" != "push" ]]; then
  echo "Publishing is restricted to main-branch pushes" >&2
  exit 1
fi

registry=036706657723.dkr.ecr.ap-south-1.amazonaws.com
repository="$registry/commerce/catalog"
image_tag="sha-${GITHUB_SHA:?}-run-${GITHUB_RUN_ID:?}-${GITHUB_RUN_ATTEMPT:?}"

aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin "$registry"
# Re-tag the exact local image that passed tests and scanning; do not rebuild.
docker tag "commerce-catalog:${APP_VERSION:?}" "$repository:$image_tag"
docker push "$repository:$image_tag"

for attempt in 1 2 3 4 5; do
  if aws ecr describe-images --region ap-south-1 --repository-name commerce/catalog \
      --image-ids "imageTag=$image_tag" --output json > reports/ecr-image.json; then
    break
  fi
  if [[ "$attempt" == 5 ]]; then exit 1; fi
  sleep 2
done
export COMMERCE_IMAGE_TAG="$image_tag"
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
detail = json.loads(Path('reports/ecr-image.json').read_text())['imageDetails'][0]
digest = detail['imageDigest']
repository = '036706657723.dkr.ecr.ap-south-1.amazonaws.com/commerce/catalog'
release = {
    'source_commit': os.environ['GITHUB_SHA'],
    'image': repository + '@' + digest,
    'tag': os.environ['COMMERCE_IMAGE_TAG'],
    'local_image_id': subprocess.check_output([
        'docker', 'image', 'inspect', 'commerce-catalog:' + os.environ['APP_VERSION'],
        '--format', '{{.Id}}'], text=True).strip(),
    'workflow_run': os.environ['GITHUB_SERVER_URL'] + '/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID'],
    'approval_status': 'candidate_pending_sonarqube_and_inspector',
    'oidc_subject': Path('reports/oidc-subject.txt').read_text().strip(),
}
Path('reports/release.json').write_text(json.dumps(release, indent=2) + '\n')
with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
    summary.write('### Published candidate\n\n`' + release['image'] + '`\n\n')
    summary.write('Source: `' + release['source_commit'] + '`\n\n')
    summary.write('SonarQube and completed Inspector policy checks are still required before promotion.\n')
print('Published candidate:', release['image'])
PY
