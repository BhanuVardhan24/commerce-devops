import json
from pathlib import Path
import subprocess
import urllib.request

result = subprocess.check_output([
    "helm", "search", "repo",
    "eks/aws-load-balancer-controller",
    "--output", "json",
], text=True)

chart = next(
    row for row in json.loads(result)
    if row["name"] == "eks/aws-load-balancer-controller"
)

folder = Path("gitops/platform/load-balancer-controller")
folder.mkdir(parents=True, exist_ok=True)

folder.joinpath("chart-version.txt").write_text(chart["version"] + "\n")

app_version = chart["app_version"]
if not app_version.startswith("v"):
    app_version = "v" + app_version

url = (
    "https://raw.githubusercontent.com/kubernetes-sigs/"
    f"aws-load-balancer-controller/{app_version}/docs/install/iam_policy.json"
)

with urllib.request.urlopen(url, timeout=30) as response:
    policy = json.load(response)

Path("infra/iam/commerce-load-balancer-controller-policy.json").write_text(
    json.dumps(policy, indent=2) + "\n"
)

folder.joinpath("controller-version.txt").write_text(app_version + "\n")

print("Chart:", chart["version"])
print("Controller:", app_version)
print("Saved matching official IAM policy.")