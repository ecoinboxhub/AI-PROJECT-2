import json
import pytest

from business_owner_ai.src.core.orchestrator import orchestrate_outbound
from business_owner_ai.src.core.trigger_detector import classify_trigger


class DummyResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data
        self.text = json.dumps(json_data)

    def json(self):
        return self._json


class FakeClient:
    """Simple stand-in for httpx.Client that returns canned responses."""
    def __init__(self, *args, **kwargs):
        pass

    def post(self, url, json=None):
        if url.endswith("/api/v1/customer/context"):
            return DummyResponse(200, {
                "customer_profile": {"name": "TestUser"},
                "conversation_history": [{"role": "customer", "message": "hi"}],
                "segments": ["vip"]
            })
        if url.endswith("/api/v1/kb/retrieve"):
            return DummyResponse(200, {
                "chunks": [{"content": "Some KB content"}],
                "summary": "Some KB content",
                "confidence": 0.85
            })
        return DummyResponse(404, {"error": "not found"})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch):
    """Monkeypatch httpx.Client used in orchestrator."""
    monkeypatch.setattr("business_owner_ai.src.core.orchestrator.httpx.Client", FakeClient)
    return monkeypatch


def test_orchestrate_b2c_success():
    trigger = classify_trigger({
        "trigger_type": "technical_fixed",
        "business_id": "biz-foo",
        "customer_id": "cust-bar",
        "context": {"issue_summary": "server down"},
        "personalization": {"first_name": "Ana"}
    })

    result = orchestrate_outbound(trigger, customer_ai_base="http://fake")
    assert result["ready_for_delivery"]
    assert "Ana" in result["message_content"]
    assert result["kb_confidence"] >= 0.6
    assert any("Calling Customer AI /api/v1/customer/context" in l for l in result["details"]["logs"])
    assert any("Calling Customer AI /api/v1/kb/retrieve" in l for l in result["details"]["logs"])
    assert "b2b_fields" not in result["details"]


def test_orchestrate_detects_b2b_field():
    trigger = classify_trigger({
        "trigger_type": "technical_fixed",
        "business_id": "biz-foo",
        "customer_id": "cust-bar",
        "context": {},
        "personalization": {},
        "account_id": "acct-123"
    })
    result = orchestrate_outbound(trigger, customer_ai_base="http://fake")
    assert "b2b_fields" in result["details"]
    assert "account_id" in result["details"]["b2b_fields"]
