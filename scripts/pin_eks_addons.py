"""Record the compatible add-on versions selected during the first apply."""
import json
import subprocess
from pathlib import Path

versions = json.loads(subprocess.check_output([
    "terraform", "-chdir=infra/environments/dev", "output", "-json", "eks_addon_versions"
], text=True))
lines = ["# Pinned from the first successful EKS apply.", "locals {", "  eks_addon_pins = {"]
for name, version in sorted(versions.items()):
    lines.append(f"    {json.dumps(name)} = {json.dumps(version)}")
lines += ["  }", "}", ""]
Path("infra/environments/dev/eks-addon-pins.tf").write_text("\n".join(lines))
subprocess.run(["terraform", "fmt", "infra/environments/dev/eks-addon-pins.tf"], check=True)
print("Recorded add-on versions:", versions)
