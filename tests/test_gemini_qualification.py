"""Gemini HTTP contract and readiness; all requests use an in-memory transport."""
import json
import socket

import httpx
from openai import AsyncOpenAI
import pytest
import pytest_asyncio

from services.llm import readiness, router

@pytest_asyncio.fixture
async def gemini(monkeypatch):
    def deny_network(*args, **kwargs):
        raise AssertionError("Gemini unit tests must not use the network")

    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    # Native Google remains supported independently of the OmniRoute qual profile.
    configuration = {"LLM_PROVIDER": "gemini", "LLM_MODEL": "gemini-3.8-flash"}
    for _, key, *_ in router._OPENAI_COMPAT_PROVIDERS:
        monkeypatch.setattr(router.settings, key, "")
    for key in ("anthropic_api_key", "custom_llm_base_url", "llm_model_large", "llm_model_small",
                "llm_model_fast", "llm_model_standard", "llm_model_frontier"):
        monkeypatch.setattr(router.settings, key, "")
    monkeypatch.setattr(router.settings, "use_litellm", False)
    monkeypatch.setattr(router.settings, "llm_required", True)
    monkeypatch.setattr(router.settings, "llm_provider", configuration["LLM_PROVIDER"])
    monkeypatch.setattr(router.settings, "llm_model", configuration["LLM_MODEL"])
    monkeypatch.setattr(router.settings, "gemini_api_key", "unit-test-placeholder")
    registry = router._build_registry()
    client = registry.get()
    await client.client.close()
    requests = []
    reply = {"status": 200, "body": {"id": configuration["LLM_MODEL"], "object": "model", "created": 0, "owned_by": "google"}}

    def respond(request):
        requests.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["authorization"] == "Bearer unit-test-placeholder"
        if "exception" in reply:
            raise reply["exception"]("simulated transport failure", request=request)
        if "sse" in reply:
            return httpx.Response(200, text=reply["sse"], headers={"content-type": "text/event-stream"})
        return httpx.Response(reply["status"], json=reply["body"])

    client.client = AsyncOpenAI(api_key="unit-test-placeholder", base_url=str(client.client.base_url),
                               http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(readiness, "get_registry", lambda: registry)
    try:
        yield client, reply, requests
    finally:
        await client.client.close()


@pytest.mark.asyncio
async def test_gemini_readiness_checks_authenticated_metadata_and_recovers(gemini):
    client, reply, requests = gemini
    assert client.provider_name == "gemini"
    assert client.model.startswith("gemini-")
    reply["status"] = 401
    reply["body"] = {"error": {"message": "simulated failure"}}
    assert (await readiness.get_llm_runtime_status())["status"] == "degraded"
    reply["status"] = 200
    reply["body"] = {"id": "models/" + client.model, "object": "model", "created": 0, "owned_by": "google"}
    assert (await readiness.get_llm_runtime_status())["status"] == "ready"
    assert len(requests) == 2  # No automatic retry, no billable generation probe.
    assert all(r.method == "GET" and r.url.path == "/v1beta/openai/models/" + client.model for r in requests)
    assert all(not r.content and r.extensions["timeout"]["read"] == 5.0 for r in requests)


@pytest.mark.asyncio
@pytest.mark.parametrize("status,category", [(401, "auth_error"), (403, "auth_error"), (404, "model_unavailable"),
                                             (429, "rate_limited"), (503, "server_error"), (400, "unexpected_status")])
async def test_gemini_probe_refuses_provider_errors_without_exposing_body(gemini, caplog, status, category):
    client, reply, requests = gemini
    reply["status"] = status
    reply["body"] = {"error": {"message": "untrusted-provider-body-do-not-publish"}}
    assert await client.ping() is False
    assert len(requests) == 1
    assert category in caplog.text
    assert "untrusted-provider-body-do-not-publish" not in caplog.text
    assert "unit-test-placeholder" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
async def test_gemini_probe_refuses_unreachable_or_timed_out_endpoint(gemini, error):
    client, reply, requests = gemini
    reply["exception"] = error
    assert await client.ping() is False
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_gemini_probe_refuses_another_model(gemini):
    client, reply, _ = gemini
    reply["body"]["id"] = "gemini-another-model"
    assert await client.ping() is False


@pytest.mark.asyncio
async def test_gemini_quiz_generation_http_contract(gemini):
    client, reply, requests = gemini
    quiz = [{"question_type": "mc", "question": "Quel tableau permet la dichotomie ?",
             "options": {"A": "Trié", "B": "Aléatoire"}, "correct_answer": "A"}]
    reply["body"] = {"id": "fixture-completion", "object": "chat.completion", "created": 0, "model": client.model,
                     "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(quiz)}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32}}
    text, usage = await client.extract("Generate a QCM from the supplied text.", "La dichotomie exige un tableau trié.")
    assert json.loads(text) == quiz
    assert usage == {"input_tokens": 12, "output_tokens": 20}
    assert len(requests) == 1
    assert requests[0].url.path == "/v1beta/openai/chat/completions"
    body = json.loads(requests[0].content)
    assert body["model"] == client.model
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


@pytest.mark.asyncio
async def test_gemini_stream_contract_keeps_usage(gemini):
    client, reply, requests = gemini
    chunks = [{"id": "fixture", "object": "chat.completion.chunk", "created": 0, "model": client.model,
               "choices": [{"index": 0, "delta": {"content": "Réponse"}, "finish_reason": None}]},
              {"id": "fixture", "object": "chat.completion.chunk", "created": 0, "model": client.model,
               "choices": [], "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}]
    reply["sse"] = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
    assert [part async for part in client.stream_chat("Teach.", "Question fixture.")] == ["Réponse"]
    assert client.get_last_usage() == {"input_tokens": 2, "output_tokens": 3}
    body = json.loads(requests[0].content)
    assert body["stream"] is True and body["stream_options"]["include_usage"] is True
