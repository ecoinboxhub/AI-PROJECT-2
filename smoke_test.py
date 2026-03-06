"""
Smoke test: B2C Outbound AI Orchestration

Run with: python smoke_test.py

Requirements: requests (pip install requests)

What it does:
- Posts three triggers to Business Owner AI /api/v1/orchestrator/triggers
  (technical_fixed, order_located, promotional_update)
- For each orchestration response, posts to Voice Agent /api/v1/outbound/session-prepare
- Validates only the essential fields (no strict personalization/log checks)
- Prints PASS/FAIL per test and a summary
"""

import os
import sys
import requests
import base64
import json
import time

BUSINESS_BASE = os.environ.get("BUSINESS_BASE", "http://localhost:8001")
VOICE_BASE = os.environ.get("VOICE_BASE", "http://localhost:8003")
TIMEOUT = 10

TESTS = [
    {
        "name": "technical_fixed",
        "payload": {
            "trigger_type": "technical_fixed",
            "business_id": "biz_123",
            "customer_id": "cust_456",
            "context": {
                "ticket_id": "tkt-001",
                "issue_summary": "Payment gateway outage",
                "resolved_at": "2026-03-01T10:00:00Z"
            },
            "personalization": {"first_name": "Alice"}
        }
    },
    {
        "name": "order_located",
        "payload": {
            "trigger_type": "order_located",
            "business_id": "biz_123",
            "customer_id": "cust_456",
            "context": {
                "order_id": "ORD-1234",
                "status": "located",
                "location": "Central Warehouse"
            },
            "personalization": {"first_name": "Bob"}
        }
    },
    {
        "name": "promotional_update",
        "payload": {
            "trigger_type": "promotional_update",
            "business_id": "biz_123",
            "customer_id": "cust_456",
            "context": {
                "offer_title": "Yearly Loyalty Discount",
                "expiry": "2026-12-31",
                "discount_percentage": 15
            },
            "personalization": {"first_name": "Carol"}
        }
    }
]

HEADERS = {"Content-Type": "application/json"}


def post_trigger(payload):
    """Post trigger to Business AI orchestrator"""
    url = f"{BUSINESS_BASE}/api/v1/orchestrator/triggers"
    r = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def post_voice_prepare(body):
    """Post to Voice Agent to prepare outbound session"""
    url = f"{VOICE_BASE}/api/v1/outbound/session-prepare"
    r = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def validate_orchestration(resp):
    """
    Validate orchestration response has essential fields.
    Only check: trace_id, message_content (non-empty), ready_for_delivery=true.
    Accept any kb_confidence value (or even null).
    Do NOT check: personalization, logs, customer_context, scenario-specific fields.
    """
    ok = True
    details = {}

    if not isinstance(resp, dict):
        return False, {"error": "orchestration response not a dict"}

    # REQUIRED: trace_id must exist
    if not resp.get("trace_id"):
        ok = False
        details.setdefault("missing", []).append("trace_id")

    # REQUIRED: message_content must be non-empty
    if not resp.get("message_content"):
        ok = False
        details.setdefault("missing", []).append("message_content")

    # REQUIRED: ready_for_delivery must be true
    if resp.get("ready_for_delivery") is not True:
        ok = False
        details["ready_for_delivery_is_false"] = resp.get("ready_for_delivery")

    # OPTIONAL: kb_confidence can be any value or null (we don't enforce it)
    details["kb_confidence"] = resp.get("kb_confidence")

    # Store key fields for debugging
    details.update({
        "trace_id": resp.get("trace_id"),
        "ready_for_delivery": resp.get("ready_for_delivery"),
        "message_content_length": len(resp.get("message_content") or "")
    })

    return ok, details


def validate_voice_response(resp):
    """
    Validate voice agent response has essential fields.
    Required: session_id, greeting.text
    Optional: greeting.audio_base64 (can be null if TTS fails)
    """
    ok = True
    details = {}

    if not isinstance(resp, dict):
        return False, {"error": "voice response not a dict"}

    # REQUIRED: session_id must exist
    if not resp.get("session_id"):
        ok = False
        details.setdefault("missing", []).append("session_id")

    greeting = resp.get("greeting") or {}

    # REQUIRED: greeting.text must be non-empty
    if not greeting.get("text"):
        ok = False
        details.setdefault("missing", []).append("greeting.text")

    # OPTIONAL: greeting.audio_base64 can be null if TTS fails
    # (ElevenLabs API might be unavailable or API key invalid)
    audio_b64 = greeting.get("audio_base64")
    if audio_b64:
        try:
            raw = base64.b64decode(audio_b64)
            details["audio_bytes_len"] = len(raw)
            if len(raw) < 50:
                ok = False
                details.setdefault("error", []).append("audio too short")
        except Exception as e:
            ok = False
            details.setdefault("error", []).append(f"audio decode error: {e}")
    else:
        details["audio_bytes_len"] = 0
        details["note"] = "TTS audio not available (API may be unavailable)"

    details["session_id"] = resp.get("session_id")
    return ok, details


def run_test_case(test):
    """Run one test case: trigger → orchestration → voice session"""
    name = test["name"]
    payload = test["payload"]
    out = {"test": name, "passed": False, "steps": []}

    try:
        # STEP 1: Post trigger to Business AI
        print(f"[+] Posting trigger '{name}' to Business AI...", flush=True)
        orch = post_trigger(payload)
        ok, d = validate_orchestration(orch)
        out["orchestration"] = {"ok": ok, "detail": d}

        if not ok:
            out["steps"].append({"orchestration": "FAIL"})
            return out

        out["steps"].append({"orchestration": "PASS"})

        # STEP 2: Prepare voice session
        voice_payload = {
            "trigger_id": orch.get("trace_id") or orch.get("trigger_id") or "",
            "trigger_type": payload.get("trigger_type"),
            "business_id": payload.get("business_id"),
            "business_name": payload.get("business_id"),
            "customer_id": payload.get("customer_id"),
            "message_content": orch.get("message_content") or "",
            "personalization": payload.get("personalization") or {},
            "tts_options": {"format": "MP3"}
        }

        print(f"[+] Posting session-prepare to Voice Agent for '{name}'...", flush=True)
        voice_resp = post_voice_prepare(voice_payload)
        vok, vd = validate_voice_response(voice_resp)
        out["voice"] = {"ok": vok, "detail": vd}

        out["steps"].append({"voice_prepare": "PASS" if vok else "FAIL"})
        out["passed"] = ok and vok
        return out

    except requests.exceptions.RequestException as e:
        out["error"] = str(e)
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


if __name__ == "__main__":
    start = time.time()
    summary = {"total": len(TESTS), "passed": 0, "failed": 0, "results": []}
    print("Smoke test: B2C Outbound Orchestration\n")
    print(f"BUSINESS_BASE={BUSINESS_BASE}  VOICE_BASE={VOICE_BASE}\n")

    for t in TESTS:
        res = run_test_case(t)
        summary["results"].append(res)
        if res.get("passed"):
            summary["passed"] += 1
            print(f"[PASS] {t['name']}\n")
        else:
            summary["failed"] += 1
            print(
                f"[FAIL] {t['name']} - details: "
                f"{json.dumps(res.get('orchestration') or res.get('voice') or res.get('error') or res, indent=2)}\n"
            )

    elapsed = time.time() - start
    print("===== SUMMARY =====")
    print(json.dumps({
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "elapsed_s": round(elapsed, 2)
    }, indent=2))

    sys.exit(2 if summary["failed"] > 0 else 0)