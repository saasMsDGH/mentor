#!/usr/bin/env python3
"""Validate a captured Argo CD/Kubernetes qualification proof, without mutation.

Snapshots must be captured by a trusted operator from the intended cluster.
This checks deployment state, not the separate functional/security/backup recipe.
"""
import argparse
import json
from pathlib import Path
import re

if __package__:
    from .render_argocd_candidate import REPOSITORY
else:
    from render_argocd_candidate import REPOSITORY


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(image):
    match = re.search(r"@(?P<digest>sha256:[0-9a-f]{64})$", image)
    require(match is not None, "Published immutable image digests are required")
    return match.group("digest")


def verify(application, deployments, replica_sets, pods, revision, images, runtime_digests=None):
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "A complete expected Git commit is required")
    require(set(images) == {"api", "web"}, "Both qualified application images are required")
    runtime_digests = runtime_digests or {name: digest(image) for name, image in images.items()}
    spec = application.get("spec", {})
    status = application.get("status", {})
    require(application.get("metadata", {}).get("name") == "mentor-qual", "Unexpected Argo CD Application")
    require(spec.get("project") == "mentor", "The application must use the bounded MENTOR project")
    require(spec.get("source", {}).get("repoURL") == REPOSITORY, "Unexpected Git repository")
    require(spec.get("source", {}).get("targetRevision") == revision, "Qualification source must pin the expected commit")
    require(spec.get("source", {}).get("path") == "k8s/overlays/qual", "Unexpected qualification source path")
    require(spec.get("destination", {}).get("namespace") == "mentor-qual", "Unexpected qualification namespace")
    require(spec.get("destination", {}).get("server") == "https://kubernetes.default.svc", "Unexpected destination cluster")
    require(set(spec.get("source", {}).get("kustomize", {}).get("images", [])) == {f"mentor-{name}={image}" for name, image in images.items()},
            "Argo CD image overrides differ from the qualified artifacts")
    require(status.get("sync", {}).get("status") == "Synced", "Application is not Synced")
    require(status.get("sync", {}).get("revision") == revision, "Argo CD is synced to a different commit")
    require(status.get("health", {}).get("status") == "Healthy", "Application is not Healthy")
    operation = status.get("operationState", {})
    require(operation.get("phase") == "Succeeded", "The sync operation has not succeeded")
    result = operation.get("syncResult", {})
    require(result.get("revision") == revision, "Last successful operation belongs to another commit")
    require(any(r.get("kind") == "Job" and r.get("name") == "mentor-migrate" and r.get("hookPhase") == "Succeeded"
                for r in result.get("resources", [])), "No successful migration hook for this operation")
    require(not any(c.get("type", "").endswith("Error") or c.get("type") in {"ExcludedResourceWarning", "RepeatedResourceWarning"}
                    for c in status.get("conditions", [])), "Application has comparison, sync or excluded-resource errors")
    proof = {"revision": revision, "namespace": "mentor-qual", "images": {}, "pods": []}
    for component, expected_image in images.items():
        digest(expected_image)
        require(re.fullmatch(r"sha256:[0-9a-f]{64}", runtime_digests[component]), "Expected runtime manifest digest is invalid")
        name = f"mentor-{component}"
        candidates = [d for d in deployments.get("items", []) if d.get("metadata", {}).get("name") == name
                      and d["metadata"].get("namespace") == "mentor-qual"]
        require(len(candidates) == 1, "Expected qualification Deployment is missing or ambiguous")
        deployment = candidates[0]
        desired = deployment.get("spec", {}).get("replicas", 0)
        deployment_status = deployment.get("status", {})
        require(desired >= 1, "A zero-replica deployment cannot qualify")
        require(deployment_status.get("observedGeneration", -1) >= deployment["metadata"].get("generation", 0), "Deployment generation has not been observed")
        require(deployment_status.get("updatedReplicas") == desired and deployment_status.get("readyReplicas", 0) >= desired
                and deployment_status.get("availableReplicas", 0) >= desired, "Deployment rollout is incomplete")
        containers = deployment["spec"]["template"]["spec"]["containers"]
        require(len(containers) == 1 and containers[0].get("name") == component and containers[0].get("image") == expected_image,
                "Deployment image differs from the qualified artifact")
        uid = deployment["metadata"].get("uid")
        deployment_revision = deployment["metadata"].get("annotations", {}).get("deployment.kubernetes.io/revision")
        require(uid and deployment_revision, "Deployment identity/revision is missing")
        current_sets = {r["metadata"]["uid"] for r in replica_sets.get("items", [])
                        if r.get("metadata", {}).get("namespace") == "mentor-qual"
                        and r["metadata"].get("annotations", {}).get("deployment.kubernetes.io/revision") == deployment_revision
                        and any(o.get("kind") == "Deployment" and o.get("uid") == uid for o in r["metadata"].get("ownerReferences", []))}
        ready = []
        for pod in pods.get("items", []):
            metadata = pod.get("metadata", {})
            if metadata.get("namespace") != "mentor-qual" or metadata.get("deletionTimestamp"):
                continue
            if not any(o.get("kind") == "ReplicaSet" and o.get("uid") in current_sets for o in metadata.get("ownerReferences", [])):
                continue
            pod_containers = pod.get("spec", {}).get("containers", [])
            if len(pod_containers) != 1 or pod_containers[0].get("image") != expected_image:
                continue
            if pod.get("status", {}).get("phase") != "Running" or not any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod["status"].get("conditions", [])):
                continue
            statuses = [c for c in pod["status"].get("containerStatuses", []) if c.get("name") == component]
            if len(statuses) != 1 or not statuses[0].get("ready") or not statuses[0].get("state", {}).get("running"):
                continue
            if not statuses[0].get("imageID", "").endswith(runtime_digests[component]):
                continue
            ready.append(metadata["name"])
        require(len(ready) >= desired, "No complete set of ready pods executing the expected runtime image digest")
        proof["images"][component] = {"reference": expected_image, "runtime_digest": runtime_digests[component]}
        proof["pods"] += ready
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("application", "deployments", "replicasets", "pods"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--api-image", required=True)
    parser.add_argument("--web-image", required=True)
    parser.add_argument("--api-runtime-digest")
    parser.add_argument("--web-runtime-digest")
    args = parser.parse_args()
    inputs = [json.loads(getattr(args, name).read_text()) for name in ("application", "deployments", "replicasets", "pods")]
    images = {"api": args.api_image, "web": args.web_image}
    runtime = {"api": args.api_runtime_digest or digest(args.api_image), "web": args.web_runtime_digest or digest(args.web_image)}
    try:
        proof = verify(*inputs, args.revision, images, runtime)
    except ValueError as exc:
        parser.exit(1, f"Qualification refused: {exc}\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
