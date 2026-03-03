"""
LangGraph customer service agent.

Graph structure:
  START → agent (LLM + tools) ─┬─ tool_calls? → execute_tools → agent (loop)
                                └─ done?       → post_process  → END

The agent uses OpenAI function calling so the model decides when to look up
products, search knowledge, book appointments, create payment links, etc.
"""

import logging
import os
import re
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from .agent_output import CustomerResponse, EscalationPayload
from .agent_tools import build_tools_for_business
from .appointment_booking_handler import AppointmentBookingHandler
from .human_behavior_simulator import get_human_behavior_simulator
from .knowledge_base import KnowledgeBaseManager
from .payment_handler import PaymentHandler
from .prompts import CustomerPrompts

logger = logging.getLogger(__name__)

_prompts = CustomerPrompts()

# ─── Graph state ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Populated before the graph runs; read-only during the loop
    business_id: str
    business_name: str
    industry: str
    channel: str
    greeting_mode: str
    time_of_day: str
    customer_id: str


# ─── System prompt builder ───────────────────────────────────────────────────

def _build_system_prompt(state: AgentState, business_data: Dict[str, Any]) -> str:
    """Build a dynamic system prompt from business context and greeting mode."""

    business_name = state.get("business_name", "our business")
    industry = state.get("industry", "general")
    channel = state.get("channel", "whatsapp")
    greeting_mode = state.get("greeting_mode", "none")
    time_of_day = state.get("time_of_day", "day")

    personality = _prompts.get_personality_for_industry(industry)
    human_instructions = _prompts.human_agent_instructions.replace(
        "{business_name}", business_name
    )

    # Inject the business owner's personality/language setting into the prompt
    ai_settings = business_data.get("ai_settings", {}) or {}
    personality_desc = ai_settings.get("personality", "")
    if personality_desc:
        language_instruction = f"BUSINESS PERSONALITY (follow this closely): {personality_desc}"
    else:
        language_instruction = "Use warm, professional standard English."
    human_instructions = human_instructions.replace(
        "{language_instruction}", language_instruction
    )

    # Business context summary
    profile = business_data.get("business_profile", {})
    products = (
        business_data.get("products", [])
        + business_data.get("products_services", [])
        + business_data.get("services", [])
    )
    product_names = ", ".join(p.get("name", "") for p in products[:15]) or "none listed"
    hours = profile.get("hours", profile.get("operating_hours", "Contact us for hours"))
    if isinstance(hours, dict):
        hours = ", ".join(f"{k}: {v}" for k, v in hours.items())

    # Greeting instruction
    if greeting_mode == "introduction":
        greeting = (
            "FIRST-TIME CUSTOMER: This customer has never chatted before. "
            "Start with a brief introduction of the business and how you can help, "
            "then respond to their message. Keep it warm and concise."
        )
    elif greeting_mode == "day_greeting":
        greeting = (
            f"FIRST MESSAGE TODAY: Start with a short time-of-day greeting "
            f"(e.g. Good {time_of_day}), then respond to their message. "
            "Do not repeat this greeting later in the same conversation."
        )
    else:
        greeting = (
            "CONVERSATION ALREADY STARTED: Do not add a greeting or repeat "
            "good morning/afternoon/evening. Continue naturally."
        )

    # Voice channel override
    voice_instruction = ""
    if channel == "voice":
        voice_instruction = (
            "\nVOICE CALL: Customer is on a phone call. "
            "Respond in 3-5 short spoken sentences. No bullet points. "
            "Simple words. Lead with the main point."
        )

    # Escalation rules from industry config
    escalation_note = (
        "\nESCALATION: If the customer explicitly asks for a human or manager, "
        "if the issue involves legal threats, fraud, medical/legal advice, or "
        "repeated unresolved complaints, you MUST say you are connecting them "
        "with a team member. Set escalation_required to true in your final answer."
    )

    return f"""{greeting}

{human_instructions}

BUSINESS CONTEXT:
- Business: {business_name}
- Industry: {industry}
- Personality: {personality.get('traits', 'helpful and professional')}
- Tone: {personality.get('tone', 'professional')}
- Products/Services: {product_names}
- Hours: {hours}

You have tools to search the knowledge base, look up product details, 
calculate order totals, check appointment availability, book appointments, 
and create payment links. Use them when you need specific information.
Do NOT make up prices, availability, or business details — call the tool.
{voice_instruction}
{escalation_note}
"""


# ─── Graph builder ───────────────────────────────────────────────────────────

MAX_TOOL_ITERATIONS = 6


def build_agent_graph(
    business_id: str,
    business_data: Dict[str, Any],
    industry: str,
    knowledge_base: KnowledgeBaseManager,
    booking_handler: AppointmentBookingHandler,
    payment_handler: PaymentHandler,
    model_name: Optional[str] = None,
):
    """
    Compile and return a LangGraph runnable for one business.

    The graph is stateless between invocations — conversation history is
    passed in via ``messages`` at invocation time.
    """

    resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model=resolved_model, api_key=api_key, temperature=0.8)

    tools = build_tools_for_business(
        business_id=business_id,
        business_data=business_data,
        knowledge_base=knowledge_base,
        booking_handler=booking_handler,
        payment_handler=payment_handler,
    )

    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    # ── Nodes ────────────────────────────────────────────────────────────

    def call_agent(state: AgentState) -> dict:
        """Invoke the LLM (with tools bound)."""
        messages = list(state["messages"])
        # Ensure system prompt is the first message
        if not messages or not isinstance(messages[0], SystemMessage):
            sys_prompt = _build_system_prompt(state, business_data)
            messages.insert(0, SystemMessage(content=sys_prompt))
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Route: if the last message has tool calls, execute them; else finish."""
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            # Guard against infinite loops
            tool_call_count = sum(
                1 for m in state["messages"]
                if hasattr(m, "tool_calls") and m.tool_calls
            )
            if tool_call_count >= MAX_TOOL_ITERATIONS:
                return "end"
            return "tools"
        return "end"

    # ── Build graph ──────────────────────────────────────────────────────

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_agent)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# ─── Invocation helper ───────────────────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[EMAIL]"),
    (re.compile(r"\b(?:\+?234|0)\d{10}\b"), "[PHONE]"),
    (re.compile(r"\b\d{10,13}\b"), "[PHONE]"),
]


def _redact_pii(text: str) -> str:
    """Strip common PII (emails, Nigerian phone numbers) before sending to the LLM."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _convert_history_to_messages(
    conversation_history: List[Dict[str, Any]],
) -> List[BaseMessage]:
    """Convert backend conversation_history dicts to LangChain messages."""
    msgs: List[BaseMessage] = []
    for turn in conversation_history:
        role = turn.get("role", "customer")
        text = turn.get("message") or turn.get("content", "")
        text = _redact_pii(text)
        if role in ("customer", "user", "human"):
            msgs.append(HumanMessage(content=text))
        else:
            msgs.append(AIMessage(content=text))
    return msgs


def _detect_intent_from_tool_calls(messages: Sequence[BaseMessage]) -> str:
    """Infer the primary intent from which tools the agent called."""
    tool_names_used = set()
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                tool_names_used.add(tc.get("name", ""))

    if "book_appointment" in tool_names_used:
        return "appointment_booking"
    if "check_appointment_availability" in tool_names_used:
        return "appointment_inquiry"
    if "create_payment_link" in tool_names_used:
        return "payment_intent"
    if "calculate_order_total" in tool_names_used:
        return "order_inquiry"
    if "get_product_info" in tool_names_used:
        return "product_inquiry"
    if "search_knowledge" in tool_names_used:
        return "general_inquiry"
    return "general_inquiry"


def _compute_confidence(messages: Sequence[BaseMessage]) -> float:
    """Derive a confidence score from how the agent answered.
    
    Tool usage indicates the agent grounded its answer in data,
    which warrants higher confidence than a pure LLM generation.
    """
    tool_call_count = sum(
        1 for m in messages if hasattr(m, "tool_calls") and m.tool_calls
    )
    if tool_call_count >= 2:
        return 0.95
    if tool_call_count == 1:
        return 0.85
    return 0.70


def _extract_token_usage(messages: Sequence[BaseMessage]) -> Dict[str, int]:
    """Aggregate prompt and completion token counts from AIMessage metadata."""
    total_prompt = 0
    total_completion = 0
    for m in messages:
        if isinstance(m, AIMessage) and hasattr(m, "response_metadata"):
            usage = m.response_metadata.get("token_usage", {})
            total_prompt += usage.get("prompt_tokens", 0)
            total_completion += usage.get("completion_tokens", 0)
    return {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
    }


def _detect_sentiment(text: str) -> str:
    """Lightweight rule-based sentiment from the customer message."""
    lower = text.lower()
    neg = ["angry", "terrible", "worst", "bad", "hate", "upset", "complain",
           "refund", "scam", "rude", "disappointing", "useless", "fraud"]
    pos = ["thanks", "thank you", "great", "love", "awesome", "perfect",
           "happy", "good", "nice", "wonderful", "excellent", "appreciate"]
    neg_count = sum(1 for w in neg if w in lower)
    pos_count = sum(1 for w in pos if w in lower)
    if neg_count > pos_count:
        return "negative"
    if pos_count > neg_count:
        return "positive"
    return "neutral"


def _check_escalation(ai_text: str, sentiment: str) -> Optional[EscalationPayload]:
    """Check the AI's final text for explicit escalation signals.
    
    Sentiment alone does NOT trigger escalation — the conversation_manager
    handles sustained-frustration and repeated-complaint escalation separately.
    """
    lower = ai_text.lower()
    escalation_phrases = [
        "connect you with", "transfer you to", "escalat",
        "speak to a manager", "speak with a human", "team member",
    ]
    if any(p in lower for p in escalation_phrases):
        severity = "high" if sentiment == "negative" else "medium"
        return EscalationPayload(
            severity=severity,
            context_summary=ai_text[:200],
            suggested_action="Connect customer with human agent",
        )
    return None


def invoke_agent(
    compiled_graph,
    customer_message: str,
    conversation_history: List[Dict[str, Any]],
    business_name: str,
    business_id: str,
    industry: str,
    customer_id: str = "",
    channel: str = "whatsapp",
    greeting_mode: str = "none",
    time_of_day: str = "day",
) -> CustomerResponse:
    """
    Run the compiled LangGraph agent and return a CustomerResponse.

    This is the single entry point the orchestrator calls.
    """
    # Build message list: prior history + current message
    messages: List[BaseMessage] = _convert_history_to_messages(conversation_history)
    messages.append(HumanMessage(content=customer_message))

    initial_state: AgentState = {
        "messages": messages,
        "business_id": business_id,
        "business_name": business_name,
        "industry": industry,
        "channel": channel,
        "greeting_mode": greeting_mode,
        "time_of_day": time_of_day,
        "customer_id": customer_id,
    }

    try:
        result = compiled_graph.invoke(initial_state)
    except Exception as exc:
        logger.error(f"Agent graph invocation failed: {exc}", exc_info=True)
        return CustomerResponse(
            success=False,
            response="Sorry, something went wrong. Please try again.",
            intent="error",
            confidence=0.0,
        )

    # Extract final AI message
    final_messages = result.get("messages", [])
    ai_text = ""
    for m in reversed(final_messages):
        if isinstance(m, AIMessage) and m.content and not (hasattr(m, "tool_calls") and m.tool_calls):
            ai_text = m.content
            break

    if not ai_text:
        ai_text = "Sorry, I couldn't process that. Could you try again?"

    # Post-process: replace AI phrases with natural Nigerian alternatives.
    # The LLM is already prompted for ultra-concise output, so we skip
    # make_ultra_concise to avoid blunt keyword-based truncation.
    simulator = get_human_behavior_simulator("professional_warm")
    ai_text = simulator.add_human_imperfections(ai_text, confidence=0.8)

    intent = _detect_intent_from_tool_calls(final_messages)
    sentiment = _detect_sentiment(customer_message)
    escalation = _check_escalation(ai_text, sentiment)
    confidence = _compute_confidence(final_messages)
    token_usage = _extract_token_usage(final_messages)

    return CustomerResponse(
        success=True,
        response=ai_text,
        intent=intent,
        confidence=confidence,
        sentiment=sentiment,
        escalation_required=escalation is not None,
        escalation=escalation,
        structured_data={
            "intent": intent,
            "channel": channel,
            "token_usage": token_usage,
        },
        conversation_stage=intent,
    )
