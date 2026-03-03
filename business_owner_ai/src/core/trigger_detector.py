"""
Trigger detection utilities for Business Owner AI

This module implements a simple rule-based classifier for inbound events
and normalizes them to the shared trigger object schema used by the
outbound orchestrator.
"""
from datetime import datetime
import uuid
from typing import Dict, Any


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def classify_trigger(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a raw event dict into a normalized trigger object.

    Expected minimal input keys in `event`:
      - trigger_type (optional): a hint like 'technical_fixed', 'order_located', 'promotional_update'
      - business_id
      - customer_id (optional)
      - context (optional dict)
      - personalization (optional dict)

    Returns a trigger object with schema documented in README above.
    """
    hint = (event.get("trigger_type") or "").lower()
    business_id = event.get("business_id") or event.get("biz") or "default"
    customer_id = event.get("customer_id") or event.get("cust")
    context = event.get("context") or {}
    personalization = event.get("personalization") or {}

    # Map hint to canonical trigger type
    if "fixed" in hint or hint == "technical_fixed":
        ttype = "technical_fixed"
    elif "order" in hint or hint in ("order_located", "order_found", "order_found_location"):
        ttype = "order_located"
    elif "promo" in hint or "coupon" in hint or hint == "promotional_update":
        ttype = "promotional_update"
    else:
        # Basic rule-based inference from context fields
        if context.get("ticket_id") or context.get("resolution"):
            ttype = "technical_fixed"
        elif context.get("order_id") or context.get("status") in ("located", "found"):
            ttype = "order_located"
        elif context.get("offer") or context.get("expiry"):
            ttype = "promotional_update"
        else:
            # default to promotional_update for low-severity notifications
            ttype = "promotional_update"

    # Priority heuristics
    if ttype == "technical_fixed":
        priority = "high"
    elif ttype == "order_located":
        priority = "normal"
    else:
        priority = "low"

    # KB query hint generation
    kb_hint = event.get("kb_query_hint")
    if not kb_hint:
        if ttype == "technical_fixed":
            kb_hint = context.get("issue_summary") or context.get("resolution") or "technical resolution steps"
        elif ttype == "order_located":
            kb_hint = f"order {context.get('order_id', '')} delivery status"
        else:
            kb_hint = context.get("offer_title") or context.get("promo_title") or "promotion details"

    trigger_obj = {
        "trigger_id": event.get("trigger_id") or f"trg-{uuid.uuid4()}",
        "trigger_type": ttype,
        "business_id": business_id,
        "customer_id": customer_id,
        "timestamp": event.get("timestamp") or _now_iso(),
        "priority": event.get("priority") or priority,
        "source": event.get("source") or "business_owner_ai",
        "context": context,
        "kb_query_hint": kb_hint,
        "personalization": personalization,
        "metadata": event.get("metadata") or {}
    }

    return trigger_obj
