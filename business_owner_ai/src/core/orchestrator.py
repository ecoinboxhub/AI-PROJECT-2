"""
Simple AI orchestrator for outbound flows in Business Owner AI

Provides `orchestrate_outbound(trigger)` which calls Customer AI for
customer context and KB, composes a message, and returns an orchestration
result suitable for passing to the Voice Agent.

This implementation is intentionally lightweight and uses HTTP requests
to Customer AI endpoints. It contains basic error handling and confidence
checks (escalate when KB confidence is low).
"""
import logging

logger = logging.getLogger(__name__)

import uuid
import time
import requests
from typing import Dict, Any, Optional
from ..core.broadcast_composer import get_broadcast_composer


CUSTOMER_AI_BASE = "http://localhost:8000"


def _make_trace_id() -> str:
    return f"trace-{uuid.uuid4()}"


def _compose_message_from_kb_and_profile(kb_resp: Dict[str, Any], profile: Dict[str, Any], trigger: Dict[str, Any]) -> Dict[str, Any]:
    # Basic composition logic: prefer KB summary, include personalization
    kb_summary = kb_resp.get("summary") or ""
    kb_conf = kb_resp.get("confidence") or 1.0
    first_name = (profile.get("customer_profile") or {}).get("name") or (trigger.get("personalization") or {}).get("first_name")

    if trigger["trigger_type"] == "technical_fixed":
        issue = trigger["context"].get("issue_summary") or trigger["context"].get("resolution") or kb_summary
        greeting = f"We fixed {issue}. Your service should be back to normal."
    elif trigger["trigger_type"] == "order_located":
        order_id = trigger["context"].get("order_id") or (trigger.get("personalization") or {}).get("order_id") or "your order"
        status = trigger["context"].get("status") or "located"
        greeting = f"Good news — your order {order_id} has been located and is {status}."
    else:
        offer = trigger["context"].get("offer") or trigger["context"].get("offer_title") or kb_summary or "a new offer"
        expiry = trigger["context"].get("expiry")
        if expiry:
            greeting = f"You qualify for {offer} valid until {expiry}."
        else:
            greeting = f"You qualify for {offer}."

    if first_name:
        message_content = f"Hi {first_name}, {greeting}"
    else:
        message_content = greeting

    return {
        "message_content": message_content,
        "kb_confidence": kb_conf,
        "kb_summary": kb_summary
    }


def orchestrate_outbound(trigger: Dict[str, Any], customer_ai_base: Optional[str] = None) -> Dict[str, Any]:
    """
    Orchestrate outbound flow for a single trigger. Calls Customer AI for
    customer context and KB retrieval, composes a final message, and
    returns an orchestration result.
    """
    customer_ai_base = customer_ai_base or CUSTOMER_AI_BASE
    trace_id = _make_trace_id()
    t0 = time.time()

    # Response template with log container
    result = {
        "trace_id": trace_id,
        "trigger_id": trigger.get("trigger_id"),
        "ready_for_delivery": False,
        "escalate": False,
        "message_content": None,
        "details": {"logs": []}
    }

    # helper for logging both to logger and result details
    def _log(msg: str):
        logger.info(msg)
        result["details"].setdefault("logs", []).append(msg)

    # --- PHASE 2.2: B2C path specificity validation ---
    b2c_types = {"technical_fixed", "order_located", "promotional_update"}
    if trigger.get("trigger_type") not in b2c_types:
        _log(f"[ORCHESTRATION] WARNING: trigger_type '{trigger.get('trigger_type')}' is not a recognized B2C type")
    # detect obvious B2B-specific fields
    b2b_fields = ["account_id", "business_contact", "company_size", "enterprise_id", "b2b_reference"]
    for fld in b2b_fields:
        if fld in trigger or fld in trigger.get("context", {}):
            _log(f"[ORCHESTRATION] B2B-specific field present: {fld}")
            result["details"].setdefault("b2b_fields", []).append(fld)

    # helper for logging both to logger and result details
    def _log(msg: str):
        logger.info(msg)
        result["details"].setdefault("logs", []).append(msg)


    try:
        # 1) Fetch customer context
        ctx_payload = {
            "customer_id": trigger.get("customer_id"),
            "business_id": trigger.get("business_id"),
            "conversation_id": trigger.get("context", {}).get("conversation_id")
        }
        
        # call customer context
        _log("[ORCHESTRATION] Calling Customer AI /api/v1/customer/context")
        try:
            resp = requests.post(
                f"{customer_ai_base}/api/v1/customer/context",
                json=ctx_payload,
                timeout=30
            )
            _log(f"[ORCHESTRATION] Customer AI response: status={resp.status_code}, "
                 f"customer_profile_received={int(resp.status_code==200)}")
            if resp.status_code != 200:
                result["details"]["customer_context_error"] = resp.text
                customer_context = {}
            else:
                customer_context = resp.json()
        except Exception as e:
            _log(f"[ORCHESTRATION] Customer context call failed: {str(e)}")
            result["details"]["customer_context_error"] = str(e)
            customer_context = {}

        # 2) Fetch KB
        kb_payload = {
            "business_id": trigger.get("business_id"),
            "customer_id": trigger.get("customer_id"),
            "trigger_type": trigger.get("trigger_type"),
            "query_hint": trigger.get("kb_query_hint"),
            "max_chunks": 5
        }
        _log("[ORCHESTRATION] Calling Customer AI /api/v1/kb/retrieve")
        try:
            kb_resp_raw = requests.post(
                f"{customer_ai_base}/api/v1/kb/retrieve",
                json=kb_payload,
                timeout=30
            )
            try:
                kb_temp = kb_resp_raw.json()
            except Exception:
                kb_temp = {}
            conf = kb_temp.get("confidence")
            num_chunks = len(kb_temp.get("chunks", [])) if isinstance(kb_temp.get("chunks", []), list) else 0
            _log(f"[ORCHESTRATION] KB response: status={kb_resp_raw.status_code}, chunks_received={num_chunks}, confidence={conf}")
            if kb_resp_raw.status_code != 200:
                result["details"]["kb_error"] = kb_resp_raw.text
                kb_resp = {"summary": "", "confidence": 0.0, "chunks": []}
            else:
                kb_resp = kb_resp_raw.json()
        except Exception as e:
            _log(f"[ORCHESTRATION] KB retrieve call failed: {str(e)}")
            result["details"]["kb_error"] = str(e)
            kb_resp = {"summary": "", "confidence": 0.0, "chunks": []}

        # 3) Compose message
        composed = _compose_message_from_kb_and_profile(kb_resp, customer_context, trigger)

        # 4) Use BroadcastComposer for optional variants (business-level)
        composer = get_broadcast_composer(trigger.get("business_id"))
        try:
            bc = composer.compose_broadcast(
                message_intent=trigger.get("trigger_type"),
                target_segment=(customer_context.get("segments") or ["customer"])[0],
                business_data={"business_profile": {"business_name": trigger.get("context", {}).get("business_name", trigger.get("business_id"))}},
                personalization_data=trigger.get("personalization")
            )
            # Prefer composer primary_message if present
            if bc.get("primary_message"):
                final_message = bc.get("primary_message")
            else:
                final_message = composed["message_content"]
        except Exception:
            final_message = composed["message_content"]

        # 5) Confidence check
        kb_conf = kb_resp.get("confidence") or composed.get("kb_confidence") or 1.0
        escalate = kb_conf < 0.6

        result.update({
            "ready_for_delivery": True,
            "escalate": escalate,
            "message_content": final_message,
            "kb_summary": kb_resp.get("summary"),
            "kb_confidence": kb_conf,
            "customer_context": customer_context,
            "duration_ms": int((time.time() - t0) * 1000)
        })

        # log presence of personalization
        fname = (trigger.get("personalization") or {}).get("first_name")
        if fname and fname not in final_message:
            _log(f"[ORCHESTRATION] WARNING: personalized first_name '{fname}' not found in message_content")

        return result

    except Exception as e:
        result["error"] = str(e)
        return result
