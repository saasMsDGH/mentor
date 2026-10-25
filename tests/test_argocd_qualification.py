"""Reject stale/empty rollout proofs; check the reviewed GitOps render contract."""
from copy import deepcopy
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.render_argocd_candidate import render
from scripts.verify_argocd_qualification import verify

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
IMAGES = {name: f"ghcr.io/saasmsdgh/mentor-{name}@sha256:{digit * 64}" for name, digit in [("api", "1"), ("web", "2")]}


def proof_inputs():
    app = render(REVISION, IMAGES["api"], IMAGES["web"])[2]
    app["status"] = {"sync": {"status": "Synced", "revision": REVISION}, "health": {"status": "Healthy"},
                     "operationState": {"phase": "Succeeded", "syncResult": {"revision": REVISION,
                        "resources": [{"kind": "Job", "name": "mentor-migrate", "hookPhase": "Succeeded"}]}}}
    deployments, sets, pods = [], [], []
    for name in ("api", "web"):
        containers = [{"name": name, "image": IMAGES[name]}]
        deployments.append({"metadata": {"name": "mentor-" + name, "namespace": "mentor-qual", "uid": "deploy-" + name,
                                          "generation": 2, "annotations": {"deployment.kubernetes.io/revision": "2"}},
                            "spec": {"replicas": 1, "template": {"spec": {"containers": containers}}},
                            "status": {"observedGeneration": 2, "updatedReplicas": 1, "readyReplicas": 1, "availableReplicas": 1}})
        sets.append({"metadata": {"uid": "set-" + name, "namespace": "mentor-qual",
                                   "ownerReferences": [{"kind": "Deployment", "uid": "deploy-" + name}],
                                   "annotations": {"deployment.kubernetes.io/revision": "2"}}})
        pods.append({"metadata": {"name": "pod-" + name, "namespace": "mentor-qual",
                                   "ownerReferences": [{"kind": "ReplicaSet", "uid": "set-" + name}]},
                     "spec": {"containers": containers},
                     "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}],
                                "containerStatuses": [{"name": name, "ready": True, "state": {"running": {"startedAt": "2026-10-25T12:00:00Z"}},
                                                        "imageID": "docker-pullable://" + IMAGES[name]}]}})
    return app, {"items": deployments}, {"items": sets}, {"items": pods}


def test_valid_qualification_proof_requires_both_executed_images():
    proof = verify(*proof_inputs(), REVISION, IMAGES)
    assert proof["revision"] == REVISION
    assert set(proof["pods"]) == {"pod-api", "pod-web"}


@pytest.mark.parametrize("case", ["old_sha", "old_operation", "unhealthy", "not_synced", "no_migration", "excluded_resource",
                                  "zero_replicas", "stale_generation", "incomplete_rollout", "wrong_image", "no_pods", "old_owner", "old_digest", "not_ready"])
def test_incomplete_or_stale_deployments_do_not_qualify(case):
    app, deployments, sets, pods = deepcopy(proof_inputs())
    if case == "old_sha": app["status"]["sync"]["revision"] = "b" * 40
    if case == "old_operation": app["status"]["operationState"]["syncResult"]["revision"] = "b" * 40
    if case == "unhealthy": app["status"]["health"]["status"] = "Progressing"
    if case == "not_synced": app["status"]["sync"]["status"] = "OutOfSync"
    if case == "no_migration": app["status"]["operationState"]["syncResult"]["resources"] = []
    if case == "excluded_resource": app["status"]["conditions"] = [{"type": "ExcludedResourceWarning"}]
    if case == "zero_replicas": deployments["items"][0]["spec"]["replicas"] = 0
    if case == "stale_generation": deployments["items"][0]["status"]["observedGeneration"] = 1
    if case == "incomplete_rollout": deployments["items"][0]["status"]["readyReplicas"] = 0
    if case == "wrong_image": deployments["items"][0]["spec"]["template"]["spec"]["containers"][0]["image"] = "mentor-api:old"
    if case == "no_pods": pods["items"] = []
    if case == "old_owner": pods["items"][0]["metadata"]["ownerReferences"][0]["uid"] = "old-set"
    if case == "old_digest": pods["items"][0]["status"]["containerStatuses"][0]["imageID"] = "containerd://sha256:" + "f" * 64
    if case == "not_ready": pods["items"][0]["status"]["conditions"][0]["status"] = "False"
    with pytest.raises(ValueError):
        verify(app, deployments, sets, pods, REVISION, IMAGES)


def test_multiarch_runtime_digests_must_be_verified_explicitly():
    app, deployments, sets, pods = proof_inputs()
    child = "sha256:" + "c" * 64
    pods["items"][0]["status"]["containerStatuses"][0]["imageID"] = "docker-pullable://ghcr.io/saasmsdgh/mentor-api@" + child
    with pytest.raises(ValueError):
        verify(app, deployments, sets, pods, REVISION, IMAGES)
    proof = verify(app, deployments, sets, pods, REVISION, IMAGES,
                   {"api": child, "web": "sha256:" + "2" * 64})
    assert proof["images"]["api"]["runtime_digest"] == child


def test_renderer_is_manual_and_has_a_limited_project():
    namespace, project, application = render(REVISION, IMAGES["api"], IMAGES["web"])
    assert namespace["metadata"]["name"] == "mentor-qual"
    assert namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    assert "automated" not in application["spec"]["syncPolicy"]
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert len(project["spec"]["sourceRepos"]) == 1
    assert {d["namespace"] for d in project["spec"]["destinations"]} == {"mentor-qual", "mentor-prod"}
    assert not any(r["kind"] in {"Secret", "Role", "RoleBinding"} for r in project["spec"]["namespaceResourceWhitelist"])
    with pytest.raises(ValueError):
        render("main", IMAGES["api"], IMAGES["web"])


@pytest.mark.parametrize("environment", ["qual", "prod"])
def test_actual_kustomize_overlay_order_storage_and_scope(environment):
    result = subprocess.run(["kubectl", "kustomize", f"k8s/overlays/{environment}"], cwd=ROOT, text=True, capture_output=True, check=True)
    resources = list(yaml.safe_load_all(result.stdout))
    assert all(r["metadata"]["namespace"] == f"mentor-{environment}" for r in resources)
    assert not any(r["kind"] in {"Secret", "Namespace", "ClusterRole", "ClusterRoleBinding"} for r in resources)
    pvc = next(r for r in resources if r["kind"] == "PersistentVolumeClaim")
    assert pvc["spec"]["storageClassName"] == "longhorn"
    for r in resources:
        if r["kind"] in {"ServiceAccount", "NetworkPolicy"}:
            assert r["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-2"
        if r["kind"] == "Deployment":
            assert r["spec"]["replicas"] == (1 if environment == "qual" else 0)
            assert r["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/part-of"] == "mentor"
    migration = next(r for r in resources if r["kind"] == "Job")
    assert migration["metadata"]["annotations"]["argocd.argoproj.io/hook"] == "Sync"
    assert migration["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-1"
    assert migration["spec"]["backoffLimit"] == 0
    credentials = migration["spec"]["template"]["spec"]["containers"][0]["env"]
    assert [e["name"] for e in credentials] == ["DATABASE_URL"]
    # A namespaceSelector and podSelector in one peer are an AND, never two OR peers.
    for r in resources:
        if r["kind"] != "NetworkPolicy": continue
        for direction, peers in [("egress", "to"), ("ingress", "from")]:
            for rule in r["spec"].get(direction, []):
                for peer in rule.get(peers, []):
                    if "namespaceSelector" in peer:
                        assert peer.get("podSelector", {}).get("matchLabels")
                    if "ipBlock" in peer:
                        assert peer["ipBlock"]["cidr"].endswith("/32")


def test_qualification_selects_gemini_without_opening_general_internet_access():
    rendered = subprocess.run(["kubectl", "kustomize", "k8s/overlays/qual"], cwd=ROOT,
                              text=True, capture_output=True, check=True)
    resources = list(yaml.safe_load_all(rendered.stdout))
    config = next(r for r in resources if r["kind"] == "ConfigMap" and r["metadata"]["name"] == "mentor-model-runtime")
    assert config["data"] == {"LLM_PROVIDER": "gemini", "LLM_MODEL": "gemini-3.8-flash"}
    api = next(r for r in resources if r["kind"] == "Deployment" and r["metadata"]["name"] == "mentor-api")
    container = api["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e for e in container["env"]}
    assert env["GEMINI_API_KEY"]["valueFrom"]["secretKeyRef"] == {"name": "mentor-model-credentials", "key": "GEMINI_API_KEY"}
    assert env["LLM_MODEL"]["valueFrom"]["configMapKeyRef"]["key"] == "LLM_MODEL"
    assert not any(name.startswith("CUSTOM_LLM_") for name in env)
    assert container["readinessProbe"]["timeoutSeconds"] > 5
    # FQDN-limited egress is an operator prerequisite, not a blanket TCP/443 grant.
    policies = [r for r in resources if r["kind"] == "NetworkPolicy"]
    assert not any(port["port"] == 443 for r in policies for rule in r["spec"].get("egress", []) for port in rule.get("ports", []))
