#!/usr/bin/env python3
"""Render an inactive/manual Argo CD candidate; never apply or synchronize it."""
import argparse
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/saasMsDGH/mentor.git"


def image_ref(value):
    if not re.fullmatch(r"ghcr\.io/saasmsdgh/mentor-(api|web)@sha256:[0-9a-f]{64}", value):
        raise argparse.ArgumentTypeError("Use an approved MENTOR GHCR repository and a published sha256 digest")
    return value


def render(revision, api_image, web_image):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Qualification requires a complete tested Git commit SHA")
    if not api_image.startswith("ghcr.io/saasmsdgh/mentor-api@") or not web_image.startswith("ghcr.io/saasmsdgh/mentor-web@"):
        raise ValueError("API and web images must match their approved repositories")
    image_ref(api_image)
    image_ref(web_image)
    return [
        yaml.safe_load((ROOT / "deploy/argocd/namespace-qual.yaml").read_text()),
        yaml.safe_load((ROOT / "deploy/argocd/project.yaml").read_text()),
        {"apiVersion": "argoproj.io/v1alpha1", "kind": "Application",
         "metadata": {"name": "mentor-qual", "namespace": "argocd"},
         "spec": {"project": "mentor", "source": {"repoURL": REPOSITORY, "targetRevision": revision,
                  "path": "k8s/overlays/qual", "kustomize": {"images": [f"mentor-api={api_image}", f"mentor-web={web_image}"]}},
                  "destination": {"server": "https://kubernetes.default.svc", "namespace": "mentor-qual"},
                  "syncPolicy": {"syncOptions": ["CreateNamespace=false"]}}},
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--api-image", type=image_ref, required=True)
    parser.add_argument("--web-image", type=image_ref, required=True)
    args = parser.parse_args()
    print(yaml.safe_dump_all(render(args.revision, args.api_image, args.web_image), sort_keys=False), end="")


if __name__ == "__main__":
    main()
