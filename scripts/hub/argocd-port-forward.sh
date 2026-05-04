#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"
CLUSTER_NAME="${CLUSTER_NAME:-AEGIS-EKS}"
NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
LOCAL_PORT="${ARGOCD_LOCAL_PORT:-8080}"
REMOTE_PORT="${ARGOCD_REMOTE_PORT:-443}"
PRINT_PASSWORD="false"

usage() {
  cat <<USAGE
Usage: $0 [--print-password]

Environment:
  AWS_REGION           AWS region. Default: ap-south-1
  CLUSTER_NAME         EKS cluster name. Default: AEGIS-EKS
  ARGOCD_NAMESPACE     ArgoCD namespace. Default: argocd
  ARGOCD_LOCAL_PORT    Local port. Default: 8080
  ARGOCD_REMOTE_PORT   ArgoCD service port. Default: 443
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-password)
      PRINT_PASSWORD="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

kubectl -n "$NAMESPACE" wait \
  --for=condition=available \
  --timeout=180s \
  deployment/argocd-server

if [[ "$PRINT_PASSWORD" == "true" ]]; then
  kubectl -n "$NAMESPACE" get secret argocd-initial-admin-secret \
    -o jsonpath='{.data.password}' | base64 -d
  echo
fi

echo "ArgoCD UI: https://127.0.0.1:${LOCAL_PORT}"
kubectl -n "$NAMESPACE" port-forward \
  service/argocd-server \
  "${LOCAL_PORT}:${REMOTE_PORT}"
