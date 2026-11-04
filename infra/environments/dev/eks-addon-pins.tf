# Pinned from the first successful EKS apply.
locals {
  eks_addon_pins = {
    "coredns"    = "v1.14.7-eksbuild.22"
    "kube-proxy" = "v1.35.3-eksbuild.62"
    "vpc-cni"    = "v1.23.2-eksbuild.8"
  }
}
