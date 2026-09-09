from fastapi.testclient import TestClient

from app.agents.llm_client import LLMClient
from app.main import app


client = TestClient(app)


def test_validation_error_shape() -> None:
    # missing required agentCategories
    res = client.post("/api/simulation/start", json={"agentCount": 1})
    assert res.status_code == 400
    payload = res.json()
    assert payload["ok"] is False
    assert payload["errorCode"] == "BAD_REQUEST"
    assert "detail" in payload


def test_http_error_shape_on_empty_upload() -> None:
    res = client.post("/api/upload", files={"file": ("empty.png", b"", "image/png")})
    assert res.status_code == 400
    payload = res.json()
    assert payload["ok"] is False
    assert payload["errorCode"] == "HTTP_ERROR"


def test_http_error_shape_on_missing_case_ref() -> None:
    payload = {
        "agentCount": 1,
        "agentCategories": ["Amplifier"],
        "description": "legacy payload without case",
    }
    res = client.post("/api/simulation/start", json=payload)
    assert res.status_code == 400
    body = res.json()
    assert body["ok"] is False
    assert body["errorCode"] == "HTTP_ERROR"


def test_llm_enabled_without_key_fallbacks() -> None:
    client_obj = LLMClient(enabled=True)
    client_obj.api_key = None
    result = client_obj.evaluate_gap({"category": "Analyst"}, {})
    assert result["gap_type"] in {"resonance", "tension", "conflict", "noise"}
    strategy = client_obj.propose_strategy("tension")
    assert strategy["action"] in {"forward", "modify", "ignore"}


def test_deepseek_chat_url_uses_v1() -> None:
    client_obj = LLMClient(enabled=False)
    client_obj.base_url = "https://api.deepseek.com"
    assert client_obj._chat_url() == "https://api.deepseek.com/v1/chat/completions"
    client_obj.base_url = "https://api.deepseek.com/v1"
    assert client_obj._chat_url() == "https://api.deepseek.com/v1/chat/completions"
    client_obj = LLMClient(enabled=False)
    client_obj.model = "deepseek-v4-pro"
    client_obj.base_url = "https://api.deepseek.com"
    payload = client_obj._with_provider_payload({"model": client_obj.model, "messages": []})
    assert payload["thinking"] == {"type": "disabled"}
    enabled = client_obj._with_provider_payload({"model": client_obj.model, "messages": []}, thinking=True)
    assert enabled["thinking"]["type"] == "enabled"


def test_message_text_and_json_extract() -> None:
    assert LLMClient._message_text({"content": "", "reasoning_content": '{"ok": true}'}) == '{"ok": true}'
    assert LLMClient._extract_json_object("```json\n{\"action\": \"modify\"}\n```") == {"action": "modify"}
    mixed = 'We need JSON only. Return JSON: {"story": "drift", "steps": [{"role": "Amplifier"}]}'
    assert LLMClient._extract_json_object(mixed) == {
        "story": "drift",
        "steps": [{"role": "Amplifier"}],
    }
    from_reasoning = LLMClient._json_from_chat_message(
        {"content": "We need answer JSON only.", "reasoning_content": '{"ok": true}'}
    )
    assert from_reasoning == {"ok": True}

