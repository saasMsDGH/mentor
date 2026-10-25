"""Offline safety contracts for the deliberately inactive qualification base."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deploy" / "kubernetes" / "base"
KUSTOMIZATION = yaml.safe_load((BASE / "kustomization.yaml").read_text())
RESOURCES = [
    resource
    for path in KUSTOMIZATION["resources"]
    for resource in yaml.safe_load_all((BASE / path).read_text())
    if resource
]


def test_qualification_base_stays_inactive_and_private():
    assert KUSTOMIZATION["namespace"] == "mentor-qualification"
    assert not any(r["kind"] in {"Ingress", "Secret", "ClusterRole", "ClusterRoleBinding"} for r in RESOURCES)
    services = [r for r in RESOURCES if r["kind"] == "Service"]
    assert services
    assert all(s["spec"]["type"] == "ClusterIP" for s in services)
    for resource in RESOURCES:
        if resource["kind"] == "Deployment":
            assert resource["spec"]["replicas"] == 0
        if resource["kind"] == "Namespace":
            assert resource["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"


def test_workloads_have_no_host_or_cluster_privileges():
    for resource in RESOURCES:
        if resource["kind"] != "Deployment":
            continue
        pod = resource["spec"]["template"]["spec"]
        assert pod["automountServiceAccountToken"] is False
        assert not any(pod.get(key) for key in ("hostNetwork", "hostPID", "hostIPC"))
        assert pod["securityContext"]["runAsNonRoot"] is True
        assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        assert not any("hostPath" in v for v in pod["volumes"])
        for container in pod["containers"]:
            security = container["securityContext"]
            assert security["allowPrivilegeEscalation"] is False
            assert security["readOnlyRootFilesystem"] is True
            assert not security.get("privileged")
            assert security["capabilities"]["drop"] == ["ALL"]
            assert container["resources"]["requests"]
            assert container["resources"]["limits"]
            assert container["livenessProbe"] and container["readinessProbe"]


def test_api_requires_secrets_authentication_and_explicit_migrations():
    api = next(r for r in RESOURCES if r["kind"] == "Deployment" and r["metadata"]["name"] == "mentor-api")
    env = {e["name"]: e for e in api["spec"]["template"]["spec"]["containers"][0]["env"]}
    expected = {"ENVIRONMENT": "production", "AUTH_ENABLED": "true", "DEPLOYMENT_MODE": "multi_user",
                "APP_AUTO_CREATE_TABLES": "false", "APP_AUTO_SEED_SYSTEM": "false",
                "ALLOW_INSECURE_PROCESS_SANDBOX": "false", "CODE_SANDBOX_BACKEND": "container"}
    assert all(env[key]["value"] == value for key, value in expected.items())
    for key in ("DATABASE_URL", "JWT_SECRET_KEY", "ENCRYPTION_KEY"):
        assert env[key]["valueFrom"]["secretKeyRef"]["key"] == key
        assert "value" not in env[key]


def test_network_defaults_deny_and_only_allow_web_api_in_same_namespace():
    policies = [r for r in RESOURCES if r["kind"] == "NetworkPolicy"]
    default = next(r["spec"] for r in policies if r["metadata"]["name"] == "default-deny-all")
    assert default["podSelector"] == {}
    assert set(default["policyTypes"]) == {"Ingress", "Egress"}
    assert default["ingress"] == default["egress"] == []
    for policy in policies:
        for direction, peers in (("ingress", "from"), ("egress", "to")):
            for rule in policy["spec"].get(direction, []):
                assert rule["ports"] == [{"protocol": "TCP", "port": 8000}]
                assert rule[peers]
                for peer in rule[peers]:
                    assert set(peer) == {"podSelector"}
                    assert peer["podSelector"]["matchLabels"]


def test_executable_workflows_use_only_organization_self_hosted_runners():
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        workflow = yaml.safe_load(path.read_text())
        for job in workflow.get("jobs", {}).values():
            labels = job["runs-on"]
            assert isinstance(labels, list), path.name
            assert "self-hosted" in labels, path.name
            assert "k8s-deploy" in labels, path.name
