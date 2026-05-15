#!/usr/bin/env python3
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def request(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.status, dict(response.headers), response.read()


def dockerhub_token(repository):
    scope = f"repository:{repository}:pull"
    query = urllib.parse.urlencode({"service": "registry.docker.io", "scope": scope})
    _, _, body = request(f"https://auth.docker.io/token?{query}")
    return json.loads(body)["token"]


def dockerhub_headers(token, accept=None):
    headers = {"Authorization": f"Bearer {token}"}
    if accept:
        headers["Accept"] = accept
    return headers


def ecr_password(region):
    result = subprocess.run(
        ["aws", "ecr", "get-login-password", "--region", region],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def ecr_headers(password, content_type=None):
    token = base64.b64encode(f"AWS:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def split_image(image):
    if ":" not in image.rsplit("/", 1)[-1]:
        return image, "latest"
    repository, tag = image.rsplit(":", 1)
    return repository, tag


def dockerhub_repository(repository):
    if "/" not in repository:
        return f"library/{repository}"
    return repository


def select_manifest(index, platform):
    os_name, arch = platform.split("/", 1)
    for manifest in index.get("manifests", []):
        item_platform = manifest.get("platform", {})
        if item_platform.get("os") == os_name and item_platform.get("architecture") == arch:
            return manifest["digest"]
    raise RuntimeError(f"No manifest found for platform {platform}")


def ecr_blob_exists(registry, repository, digest, headers):
    url = f"https://{registry}/v2/{repository}/blobs/{digest}"
    try:
        status, _, _ = request(url, method="HEAD", headers=headers)
        return status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def upload_blob(registry, repository, digest, blob, headers):
    if ecr_blob_exists(registry, repository, digest, headers):
        return

    start_url = f"https://{registry}/v2/{repository}/blobs/uploads/"
    status, response_headers, _ = request(start_url, method="POST", headers=headers)
    if status not in (202,):
        raise RuntimeError(f"Unexpected upload start status {status}")

    location = response_headers["Location"]
    if location.startswith("/"):
        location = f"https://{registry}{location}"
    separator = "&" if "?" in location else "?"
    upload_url = f"{location}{separator}digest={urllib.parse.quote(digest, safe=':')}"
    status, _, _ = request(upload_url, method="PUT", headers=headers, data=blob)
    if status not in (201, 202):
        raise RuntimeError(f"Unexpected blob upload status {status}")


def put_manifest(registry, repository, tag, manifest, media_type, headers):
    url = f"https://{registry}/v2/{repository}/manifests/{tag}"
    put_headers = dict(headers)
    put_headers["Content-Type"] = media_type
    status, _, _ = request(url, method="PUT", headers=put_headers, data=manifest)
    if status not in (200, 201, 202):
        raise RuntimeError(f"Unexpected manifest put status {status}")


def main():
    parser = argparse.ArgumentParser(description="Copy one public image platform from Docker Hub to ECR")
    parser.add_argument("--source", required=True, help="Docker Hub image, for example nginxinc/nginx-unprivileged:stable-alpine")
    parser.add_argument("--target-registry", required=True, help="ECR registry host")
    parser.add_argument("--target-repository", required=True, help="ECR repository name")
    parser.add_argument("--target-tags", required=True, help="Comma-separated tags to write")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-south-1"))
    parser.add_argument("--platform", default="linux/arm64")
    args = parser.parse_args()

    source_repository, source_tag = split_image(args.source)
    source_repository = dockerhub_repository(source_repository)
    token = dockerhub_token(source_repository)

    manifest_url = f"https://registry-1.docker.io/v2/{source_repository}/manifests/{source_tag}"
    _, index_headers, index_body = request(manifest_url, headers=dockerhub_headers(token, MANIFEST_ACCEPT))
    index_type = index_headers.get("Content-Type", "")
    index = json.loads(index_body)

    if index_type.startswith("application/vnd.oci.image.index") or index_type.startswith(
        "application/vnd.docker.distribution.manifest.list"
    ):
        digest = select_manifest(index, args.platform)
        _, manifest_headers, manifest_body = request(
            f"https://registry-1.docker.io/v2/{source_repository}/manifests/{digest}",
            headers=dockerhub_headers(token, MANIFEST_ACCEPT),
        )
    else:
        manifest_headers = index_headers
        manifest_body = index_body

    manifest_type = manifest_headers.get("Content-Type", "application/vnd.oci.image.manifest.v1+json")
    manifest = json.loads(manifest_body)

    password = ecr_password(args.region)
    headers = ecr_headers(password)

    descriptors = [manifest["config"]] + manifest.get("layers", [])
    for descriptor in descriptors:
        digest = descriptor["digest"]
        _, _, blob = request(
            f"https://registry-1.docker.io/v2/{source_repository}/blobs/{digest}",
            headers=dockerhub_headers(token),
        )
        upload_blob(args.target_registry, args.target_repository, digest, blob, headers)

    for tag in [item.strip() for item in args.target_tags.split(",") if item.strip()]:
        put_manifest(args.target_registry, args.target_repository, tag, manifest_body, manifest_type, headers)
        print(f"pushed {args.target_registry}/{args.target_repository}:{tag}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
