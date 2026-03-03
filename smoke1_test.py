"""
Smoke test: B2C Outbound AI Orchestration

Run with: python smoke_test.py

Requirements: requests (pip install requests)
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
    url = f"{BUSINESS_BASE}/api/v1/orchestrator/triggers"
    r = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def post_voice_prepare(body):
    url = f"{VOICE_BASE}/api/v1/outbound/session-prepare"
    r = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def validate_orchestration(resp):
    """
    Only check that the server returned a valid orchestration response.
    Required: trace_id exists, message_content is non-empty, ready_for_delivery is true.
    kb_confidence just needs to be present (any value is accepted).
    No strict personalization, log, or customer context checks.
    """
    ok = True
    details = {}

    if not isinstance(resp, dict):
        return False, {"error": "orchestration response not a dict"}

    # trace_id must exist
    if not resp.get("trace_id"):
        ok = False
        details.setdefault("missing", []).append("trace_id")

    # message_content must exist and be non-empty
    if not resp.get("message_content"):
        ok = False
        details.setdefault("missing", []).append("message_content")

    # ready_for_delivery must be true
    if not resp.get("ready_for_delivery"):
        ok = False
        details["ready_for_delivery"] = resp.get("ready_for_delivery")

    # kb_confidence must be present (any value accepted)
    if "kb_confidence" not in resp:
        ok = False
        details.setdefault("missing", []).append("kb_confidence")

    details.update({
        "trace_id": resp.get("trace_id"),
        "ready_for_delivery": resp.get("ready_for_delivery"),
        "kb_confidence": resp.get("kb_confidence")
    })

    return ok, details


def validate_voice_response(resp):
    """
    Only check that the server returned a valid voice session response.
    Required: session_id exists, greeting.text is non-empty, greeting.audio_base64 is non-empty.
    """
    ok = True
    details = {}

    if not isinstance(resp, dict):
        return False, {"error": "voice response not a dict"}

    # session_id must exist
    if not resp.get("session_id"):
        ok = False
        details.setdefault("missing", []).append("session_id")

    greeting = resp.get("greeting") or {}

    # greeting.text must be non-empty
    if not greeting.get("text"):
        ok = False
        details.setdefault("missing", []).append("greeting.text")

    # greeting.audio_base64 must be non-empty and decodable
    audio_b64 = greeting.get("audio_base64")
    if not audio_b64:
        ok = False
        details.setdefault("missing", []).append("greeting.audio_base64")
    else:
        try:
            raw = base64.b64decode(audio_b64)
            details["audio_bytes_len"] = len(raw)
            if len(raw) < 50:
                ok = False
                details.setdefault("error", []).append("audio too short")
        except Exception as e:
            ok = False
            details.setdefault("error", []).append(f"audio decode error: {e}")

    details["session_id"] = resp.get("session_id")
    return ok, details


def run_test_case(test):
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

        # STEP 2: Post to Voice Agent
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