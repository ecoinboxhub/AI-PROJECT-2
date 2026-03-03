"""
LangGraph agent tools.
Each tool wraps an existing handler (knowledge base, booking, payment) so
the LLM can decide when to call them during the agent loop.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool

from .knowledge_base import KnowledgeBaseManager
from .appointment_booking_handler import AppointmentBookingHandler
from .payment_handler import PaymentHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Factory: build the tool list for a specific business at runtime.
# We need closures over the business-specific handlers and data.
# ---------------------------------------------------------------------------

def build_tools_for_business(
    business_id: str,
    business_data: Dict[str, Any],
    knowledge_base: KnowledgeBaseManager,
    booking_handler: AppointmentBookingHandler,
    payment_handler: PaymentHandler,
) -> list:
    """Return a list of LangChain tool objects bound to one business."""

    # ── RAG retrieval ────────────────────────────────────────────────────
    @tool
    def search_knowledge(query: str) -> str:
        """Search the business knowledge base (products, services, FAQs,
        policies, hours) for information relevant to the customer query.
        Call this whenever you need business-specific facts you don't
        already have in context."""
        try:
            results = knowledge_base.retrieve_relevant_knowledge(
                business_id=business_id,
                query=query,
                n_results=5,
            )
            if not results.get("success") or not results.get("documents"):
                return "No relevant information found in the knowledge base."
            docs = results["documents"]
            parts = []
            for doc in docs:
                if doc.get("relevance_score", 0) > 0.4:
                    parts.append(doc["content"])
            return "\n\n".join(parts) if parts else "No highly relevant results."
        except Exception as exc:
            logger.error(f"search_knowledge error: {exc}")
            return f"Knowledge search failed: {exc}"

    # ── Product / service lookup ─────────────────────────────────────────
    @tool
    def get_product_info(product_name: str) -> str:
        """Look up a specific product or service by name and return its
        details (price, description, availability). Use this when the
        customer asks about a particular item."""
        products = business_data.get("products", []) + business_data.get(
            "products_services", []
        ) + business_data.get("services", [])
        matches = [
            p for p in products
            if product_name.lower() in (p.get("name", "") or "").lower()
        ]
        if not matches:
            return f"No product or service matching '{product_name}' found."
        lines = []
        for p in matches[:3]:
            name = p.get("name", "Unknown")
            price = p.get("price")
            desc = p.get("description", "")
            avail = p.get("availability", True)
            line = f"{name}"
            if price is not None:
                line += f" — price: {price}"
            if desc:
                line += f" — {desc}"
            if not avail:
                line += " (currently unavailable)"
            lines.append(line)
        return "\n".join(lines)

    # ── Order total ──────────────────────────────────────────────────────
    @tool
    def calculate_order_total(items_json: str) -> str:
        """Calculate the total cost for an order.  `items_json` is a JSON
        array like [{"name": "Sausage roll", "quantity": 2}].
        Returns an itemised breakdown with a total."""
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            return "Could not parse items. Provide a JSON array of {name, quantity}."
        products = business_data.get("products", []) + business_data.get(
            "products_services", []
        ) + business_data.get("services", [])
        product_map = {
            (p.get("name", "") or "").lower(): p for p in products
        }
        lines = []
        total = 0.0
        for item in items:
            name = item.get("name", "")
            qty = int(item.get("quantity", 1))
            match = product_map.get(name.lower())
            if not match:
                lines.append(f"{name}: not found")
                continue
            price = float(match.get("price", 0))
            subtotal = price * qty
            total += subtotal
            lines.append(f"{qty}x {match.get('name', name)}: ₦{price:,.0f} each = ₦{subtotal:,.0f}")
        lines.append(f"TOTAL: ₦{total:,.0f}")
        return "\n".join(lines)

    # ── Appointment availability ─────────────────────────────────────────
    @tool
    def check_appointment_availability(date: str, service: str = "") -> str:
        """Check available appointment slots for a given date (YYYY-MM-DD).
        Optionally filter by service name."""
        try:
            result = booking_handler.check_availability(
                service_id=service or "default",
                date=date,
            )
            if not result.get("success"):
                return f"Could not check availability: {result.get('error', 'unknown error')}"
            slots = result.get("available_slots", [])
            if not slots:
                return f"No available slots on {date}."
            slot_strs = [f"{s['start']} – {s['end']}" for s in slots]
            return f"Available slots on {date}: " + ", ".join(slot_strs)
        except Exception as exc:
            logger.error(f"check_appointment_availability error: {exc}")
            return f"Availability check failed: {exc}"

    # ── Book appointment ─────────────────────────────────────────────────
    @tool
    def book_appointment(
        date: str,
        time: str,
        service: str,
        customer_name: str,
        customer_contact: str = "",
        customer_id: str = "",
    ) -> str:
        """Book an appointment. Provide date (YYYY-MM-DD), time (HH:MM),
        service name, customer name, and optionally customer phone/email
        and customer_id."""
        try:
            dt_str = f"{date}T{time}:00"
            resolved_customer_id = customer_id or customer_name
            result = booking_handler.book_appointment(
                customer_id=resolved_customer_id,
                customer_name=customer_name,
                customer_contact=customer_contact,
                service_id=service,
                service_name=service,
                appointment_datetime=dt_str,
            )
            if not result.get("success"):
                return f"Booking failed: {result.get('error', 'unknown error')}"
            return f"Appointment booked: {service} on {date} at {time} for {customer_name}."
        except Exception as exc:
            logger.error(f"book_appointment error: {exc}")
            return f"Booking failed: {exc}"

    # ── Payment link ─────────────────────────────────────────────────────
    @tool
    def create_payment_link(
        customer_id: str,
        amount: Optional[float] = None,
        reference: Optional[str] = None,
    ) -> str:
        """Create a payment link for the customer. Returns a URL the
        customer can use to pay."""
        try:
            result = payment_handler.create_payment_link(
                customer_id=customer_id,
                amount=amount,
                reference=reference,
            )
            if not result.get("success"):
                return f"Could not create payment link: {result.get('error', 'unknown error')}"
            url = result.get("payment_url", "")
            return f"Payment link created: {url}"
        except Exception as exc:
            logger.error(f"create_payment_link error: {exc}")
            return f"Payment link creation failed: {exc}"

    return [
        search_knowledge,
        get_product_info,
        calculate_order_total,
        check_appointment_availability,
        book_appointment,
        create_payment_link,
    ]
