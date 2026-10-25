"""Exercise the configured internal gateway through the real SDK, without network."""
import json
from pathlib import Path
import socket

import httpx
from openai import AsyncOpenAI
import pytest
import pytest_asyncio
import yaml

from services.llm import readiness, router

ROOT = Path(__file__).resolve().parents[1]


@pytest_asyncio.fixture
async def gateway(monkeypatch):
    def deny_network(*args, **kwargs):
        raise AssertionError("OmniRoute unit tests must not contact a real service")

    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    config = yaml.safe_load((ROOT / "k8s/overlays/qual/model.yaml").read_text())["data"]
    for _, key, *_ in router._OPENAI_COMPAT_PROVIDERS:
        monkeypatch.setattr(router.settings, key, "")
    for key in ("anthropic_api_key", "llm_model_large", "llm_model_small", "llm_model_fast",
                "llm_model_standard", "llm_model_frontier"):
        monkeypatch.setattr(router.settings, key, "")
    monkeypatch.setattr(router.settings, "use_litellm", False)
    monkeypatch.setattr(router.settings, "llm_required", True)
    for field in ("llm_provider", "custom_llm_base_url", "custom_llm_model"):
        monkeypatch.setattr(router.settings, field, config[field.upper()])
    monkeypatch.setattr(router.settings, "custom_llm_api_key", "unit-test-placeholder")
    registry = router._build_registry()
    client = registry.get()
    await client.client.close()
    reply = {"status": 200, "body": {"object": "list", "data": [{"id": config["CUSTOM_LLM_MODEL"],
                     "object": "model", "created": 0, "owned_by": "gemini"}]}}
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.host == "omniroute.omniroute.svc.cluster.local"
        assert request.headers["authorization"] == "Bearer unit-test-placeholder"
        return httpx.Response(reply["status"], json=reply["body"])

    client.client = AsyncOpenAI(api_key="unit-test-placeholder", base_url=config["CUSTOM_LLM_BASE_URL"],
                               http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(readiness, "get_registry", lambda: registry)
    try:
        yield client, reply, requests
    finally:
        await client.client.close()


@pytest.mark.asyncio
async def test_gateway_readiness_requires_bearer_and_exact_gemini_route(gateway):
    client, _, requests = gateway
    assert client.provider_name == "custom"
    assert (await readiness.get_llm_runtime_status())["status"] == "ready"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET" and request.url.path == "/v1/models"
    assert not request.content
    assert request.extensions["timeout"]["read"] == 5.0


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
async def test_gateway_failure_is_not_readiness_and_does_not_log_body(gateway, caplog, status):
    _, reply, requests = gateway
    reply["status"] = status
    reply["body"] = {"error": {"message": "untrusted-gateway-error-body"}}
    assert (await readiness.get_llm_runtime_status())["status"] == "degraded"
    assert len(requests) == 1  # No retries or fallback generation.
    assert "untrusted-gateway-error-body" not in caplog.text
    assert "unit-test-placeholder" not in caplog.text


@pytest.mark.asyncio
async def test_gateway_refuses_missing_model_and_recovers(gateway):
    client, reply, requests = gateway
    models = reply["body"]["data"]
    reply["body"]["data"] = []
    assert await client.ping() is False
    reply["body"]["data"] = models
    assert await client.ping() is True
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_gateway_generation_uses_qualified_model_and_same_credential(gateway):
    client, reply, requests = gateway
    reply["body"] = {"id": "fixture-completion", "object": "chat.completion", "created": 0,
                     "model": client.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"},
                     "finish_reason": "stop"}], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}
    result, usage = await client.chat("Synthetic fixture only.", "Reply OK.")
    assert result == "OK" and usage["output_tokens"] == 1
    assert len(requests) == 1 and requests[0].url.path == "/v1/chat/completions"
    assert json.loads(requests[0].content)["model"] == "gemini/gemini-3.1-flash-lite"
