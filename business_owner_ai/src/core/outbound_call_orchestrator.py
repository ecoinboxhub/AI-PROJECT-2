"""
Outbound Call Orchestrator for Business Owner AI

Handles complete outbound call workflow:
1. Receive outbound call requests
2. Retrieve customer phone number and context
3. Fetch knowledge base information
4. Package call context for Voice Agent
5. Trigger outbound call
6. Track call state and log results
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory call state storage (for production, use a database)
call_states: Dict[str, Dict[str, Any]] = {}
call_results: Dict[str, Dict[str, Any]] = {}


class CallState:
    """Represents the current state of an outbound call"""
    
    PENDING = "pending"
    DIALING = "dialing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    
    @staticmethod
    def is_terminal(state: str) -> bool:
        return state in [CallState.COMPLETED, CallState.FAILED, CallState.ESCALATED]


class CallResult:
    """Structured call outcome"""
    
    def __init__(
        self,
        customer_id: str,
        call_id: str,
        call_status: str,
        outcome: str,
        summary: str,
        follow_up_required: bool = False,
        timestamp: Optional[datetime] = None
    ):
        self.customer_id = customer_id
        self.call_id = call_id
        self.call_status = call_status
        self.outcome = outcome
        self.summary = summary
        self.follow_up_required = follow_up_required
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "call_id": self.call_id,
            "call_status": self.call_status,
            "outcome": self.outcome,
            "summary": self.summary,
            "follow_up_required": self.follow_up_required,
            "timestamp": self.timestamp.isoformat()
        }


def create_call_context(
    customer_id: str,
    phone_number: str,
    business_id: str,
    business_name: str,
    call_purpose: str,
    call_type: str = "outbound",
    campaign_id: Optional[str] = None,
    relevant_products: Optional[List[Dict[str, Any]]] = None,
    promotion_details: Optional[Dict[str, Any]] = None,
    conversation_goal: str = "inform"
) -> Dict[str, Any]:
    """
    Create a complete call context object for Voice Agent
    
    Args:
        customer_id: Unique customer identifier
        phone_number: Customer's phone number (with country code)
        business_id: Business identifier
        business_name: Display name of business
        call_purpose: Why the call is being made
        call_type: Type of call (inbound/outbound)
        campaign_id: Optional campaign identifier
        relevant_products: Products/services to mention
        promotion_details: Promotion details if applicable
        conversation_goal: Primary goal of the conversation
    
    Returns:
        Complete call context dictionary
    """
    return {
        "customer_id": customer_id,
        "customer_phone": phone_number,
        "business_id": business_id,
        "business_name": business_name,
        "call_purpose": call_purpose,
        "call_type": call_type,
        "campaign_id": campaign_id,
        "relevant_products_or_services": relevant_products or [],
        "promotion_details": promotion_details or {},
        "conversation_goal": conversation_goal,
        "created_at": datetime.utcnow().isoformat()
    }


def store_call_state(call_id: str, state: Dict[str, Any]) -> bool:
    """Store or update call state"""
    call_states[call_id] = {
        **state,
        "updated_at": datetime.utcnow().isoformat()
    }
    return True


def get_call_state(call_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve call state by ID"""
    return call_states.get(call_id)


def update_call_state(call_id: str, updates: Dict[str, Any]) -> bool:
    """Update call state with new information"""
    if call_id not in call_states:
        return False
    
    call_states[call_id].update(updates)
    call_states[call_id]["updated_at"] = datetime.utcnow().isoformat()
    return True


def log_call_result(call_result: CallResult) -> bool:
    """Store structured call result"""
    call_results[call_result.call_id] = call_result.to_dict()
    return True


def get_call_result(call_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve call result by ID"""
    return call_results.get(call_id)


def get_all_call_results(
    customer_id: Optional[str] = None,
    business_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get call results with optional filtering"""
    results = list(call_results.values())
    
    if customer_id:
        results = [r for r in results if r.get("customer_id") == customer_id]
    
    if business_id:
        results = [r for r in results if r.get("business_id") == business_id]
    
    return results[:limit]


def check_call_cooldown(
    customer_id: str,
    business_id: str,
    cooldown_hours: int = 24
) -> bool:
    """
    Check if customer should be called again based on cooldown period
    
    Returns True if call is allowed, False if on cooldown
    """
    recent_results = get_all_call_results(customer_id=customer_id, business_id=business_id)
    
    if not recent_results:
        return True
    
    last_call = max(
        (r for r in recent_results if r.get("timestamp")),
        key=lambda x: x.get("timestamp", ""),
        default=None
    )
    
    if not last_call:
        return True
    
    try:
        last_call_time = datetime.fromisoformat(last_call["timestamp"])
        hours_since_last_call = (datetime.utcnow() - last_call_time).total_seconds() / 3600
        return hours_since_last_call >= cooldown_hours
    except Exception:
        return True
