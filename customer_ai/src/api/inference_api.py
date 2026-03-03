"""
Inference API for Customer AI (LangGraph agent backend).
AI inference endpoints only — no business logic.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio

from ..core.customer_ai_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


# Pydantic request/response models
class BusinessInfo(BaseModel):
    """Business information structure"""
    name: str = Field(..., description="Business name")
    description: Optional[str] = Field("", description="Business description")
    phone: Optional[str] = Field("", description="Business phone number")
    email: Optional[str] = Field(None, description="Business email")
    address: Optional[str] = Field("", description="Business address")
    timezone: str = Field("Africa/Lagos", description="Business timezone")
    whatsapp_number: Optional[str] = Field(None, description="WhatsApp display phone number")


class Product(BaseModel):
    """Product structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    availability: bool = True
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Service(BaseModel):
    """Service structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    availability: bool = True
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FAQ(BaseModel):
    """FAQ structure"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None


class Policies(BaseModel):
    """Business policies"""
    return_policy: Optional[str] = Field("", description="Return/refund policy")
    shipping_policy: Optional[str] = Field("", description="Shipping policy")
    payment_methods: Optional[str] = Field("", description="Accepted payment methods")


class AISettings(BaseModel):
    """AI configuration settings"""
    personality: str = Field("professional", description="AI personality type")
    language: str = Field("en", description="Response language")
    response_style: str = Field("professional_friendly", description="Response style")
    enable_tools: List[str] = Field(default_factory=lambda: ["product_search"], description="List of enabled tools")


class KnowledgeData(BaseModel):
    """Complete business knowledge data structure matching backend payload"""
    business_info: BusinessInfo
    products: List[Product] = Field(default_factory=list, description="List of products")
    services: List[Service] = Field(default_factory=list, description="List of services (can be empty)")
    faqs: List[FAQ] = Field(default_factory=list, description="Frequently asked questions")
    policies: Optional[Policies] = Field(default_factory=lambda: Policies(return_policy="", shipping_policy="", payment_methods=""), description="Business policies")
    business_hours: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Business operating hours (day-based structure with open/close/is_closed)")
    ai_settings: Optional[AISettings] = Field(default=None, description="AI configuration settings")
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "business_info": {
                    "name": "Example Business",
                    "description": "A great business",
                    "phone": "+1234567890",
                    "email": "contact@example.com",
                    "address": "123 Main St",
                    "timezone": "Africa/Lagos",
                    "whatsapp_number": "+1234567890"
                },
                "products": [],
                "services": [],
                "faqs": [],
                "policies": {
                    "return_policy": "",
                    "shipping_policy": "",
                    "payment_methods": ""
                },
                "business_hours": {
                    "monday": {"open": "09:00", "close": "17:00", "is_closed": False}
                },
                "ai_settings": {
                    "personality": "professional",
                    "language": "en",
                    "response_style": "professional_friendly",
                    "enable_tools": ["product_search", "check_availability", "book_appointment"]
                }
            }
        }


class ChatRequest(BaseModel):
    message: str = Field(..., description="Customer message")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context. Keys: conversation_id (stable per chat), channel (e.g. 'whatsapp', 'voice'), "
        "is_first_interaction (bool) = first time ever → AI gives introduction, "
        "is_new_day (bool) = first message today / after 24h → AI gives time-of-day greeting, "
        "conversation_history (list of {role: 'customer'|'ai', message: '...'}) = prior turns for follow-up and memory. "
        "Send conversation_history on every request so the AI can answer follow-ups (e.g. 'Yes', 'Yes pls')."
    )


class IntentRequest(BaseModel):
    message: str = Field(..., description="Message to analyze")


class SentimentRequest(BaseModel):
    message: str = Field(..., description="Message to analyze")


class FeedbackRequest(BaseModel):
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier (use when conversation was scoped by conversation_id)")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context with customer_id/conversation_id (matches process_customer_message scoping)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")


class EscalationRequest(BaseModel):
    """Escalation registration - called by backend when escalation_required in chat response"""
    conversation_id: str = Field(..., description="Conversation identifier")
    customer_id: str = Field(..., description="Customer identifier")
    reason: str = Field(..., description="Escalation reason (e.g., complaint_severity_high)")
    severity: str = Field(..., description="Severity level: critical, high, medium, low")
    context_summary: str = Field(..., description="Summary of conversation context")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Recent conversation turns")
    customer_message: Optional[str] = Field(None, description="Last customer message")
    ai_response: Optional[str] = Field(None, description="Last AI response")


class InferenceAPI:
    """
    Minimal inference API for Customer AI system
    Focus: AI inference endpoints only
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="ndara.ai Customer AI - Inference API",
            description="AI inference endpoints powered by LangGraph agent",
            version="3.0.0"
        )
        
        # Enable CORS
        # Get CORS origins from environment (default to "*" for development)
        cors_origins = os.getenv('CORS_ORIGINS', '*')
        if cors_origins == '*':
            # Development mode - allow all origins
            # Note: Cannot use credentials with wildcard origins (CORS spec)
            allow_origins = ["*"]
            allow_credentials = False
        else:
            # Production mode - specific origins (comma-separated)
            # Can use credentials with specific origins
            allow_origins = [origin.strip() for origin in cors_origins.split(',')]
            allow_credentials = True
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Get orchestrator
        self.orchestrator = get_orchestrator()
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Inference API initialized")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "ndara.ai Customer AI",
                "version": "3.0.0",
                "framework": "LangGraph",
                "status": "operational",
                "docs": "/docs",
                "health": "/health"
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            status = self.orchestrator.get_system_status()
            return {
                "status": "healthy" if status['success'] else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "details": status
            }
        
        @self.app.post("/api/v1/onboard")
        async def onboard_business(
            business_id: Optional[str] = None,
            body: Dict[str, Any] = Body(...)
        ):
            """
            Onboard a new business and train AI
            
            Supports two formats for backward compatibility:
            1. New format: business_id as query parameter, KnowledgeData in body
               POST /api/v1/onboard?business_id=1
               Body: { "business_info": {...}, "products": [...], ... }
            
            2. Legacy format: business_id in request body (wrapped)
               POST /api/v1/onboard
               Body: { "business_id": "1", "business_data": {...} }
            
            Args:
                business_id: Business identifier (query parameter, optional for legacy support)
                body: Request body - either KnowledgeData directly or legacy format with business_id and business_data
            
            Returns:
                - success: bool
                - business_id: str
                - industry: str
                - confidence: float
                - generated_faqs: list
                - ai_context: dict
                - model_info: dict
            """
            try:
                # Determine business_id and knowledge_data based on format
                if business_id is None:
                    # Legacy format: business_id in body
                    business_id = body.get('business_id')
                    if not business_id:
                        raise HTTPException(
                            status_code=400,
                            detail="business_id is required (either as query parameter or in request body)"
                        )
                    # Extract business_data from legacy format
                    business_data_dict = body.get('business_data', body)
                else:
                    # New format: business_id from query parameter
                    # Body should be KnowledgeData structure
                    business_data_dict = body
                
                # Validate knowledge_data structure
                try:
                    # Try to parse as KnowledgeData to validate structure
                    knowledge_data = KnowledgeData(**business_data_dict)
                    # Convert Pydantic model to dict for orchestrator
                    if hasattr(knowledge_data, 'model_dump'):
                        business_data_dict = knowledge_data.model_dump()
                    else:
                        business_data_dict = knowledge_data.dict()
                    
                    # Provide defaults for missing optional fields
                    if business_data_dict.get('ai_settings') is None:
                        business_data_dict['ai_settings'] = {
                            'personality': 'professional',
                            'language': 'en',
                            'response_style': 'professional_friendly',
                            'enable_tools': ['product_search']
                        }
                    if not business_data_dict.get('business_hours'):
                        business_data_dict['business_hours'] = {}
                    if not business_data_dict.get('policies'):
                        business_data_dict['policies'] = {
                            'return_policy': '',
                            'shipping_policy': '',
                            'payment_methods': ''
                        }
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid knowledge_data structure: {str(e)}"
                    )
                
                result = self.orchestrator.onboard_business(
                    business_id,
                    business_data_dict
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error onboarding business: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/chat")
        async def chat(business_id: str, request: ChatRequest):
            """
            Process customer message and generate AI response
            
            Args:
                business_id: Business identifier (query param)
                request: Chat request with message, customer_id, context
            
            Returns:
                - success: bool
                - response: str (AI generated response)
                - intent: str
                - sentiment: str
                - confidence: float
                - escalation_required: bool
                - structured_data: dict (e.g., appointment details, product info)
            """
            try:
                # Ensure business_id is a string for consistency
                business_id = str(business_id)
                
                # Log for debugging
                logger.info(f"Processing chat for business_id: {business_id}, message: {request.message[:50]}...")
                
                result = self.orchestrator.process_customer_message(
                    business_id=business_id,
                    customer_message=request.message,
                    customer_id=request.customer_id,
                    context=request.context
                )
                
                if not result['success']:
                    error_detail = result.get('error', 'Unknown error')
                    logger.error(f"Chat failed for business_id {business_id}: {error_detail}")
                    raise HTTPException(status_code=400, detail=error_detail)
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing chat: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/extract-intent")
        async def extract_intent(business_id: str, request: IntentRequest):
            """
            Extract intent from customer message
            
            Returns:
                - success: bool
                - intent: str (e.g., 'book_appointment', 'product_inquiry', 'complaint')
                - confidence: float
                - entities: dict (extracted entities like dates, products, locations)
                - metadata: dict
            """
            try:
                result = self.orchestrator.extract_intent(business_id, request.message)
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error extracting intent: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/analyze-sentiment")
        async def analyze_sentiment(business_id: str, request: SentimentRequest):
            """
            Analyze sentiment of customer message
            
            Returns:
                - success: bool
                - sentiment: str ('positive', 'negative', 'neutral')
                - score: float (-1.0 to 1.0)
                - confidence: float
            """
            try:
                result = self.orchestrator.analyze_sentiment(business_id, request.message)
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error analyzing sentiment: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/feedback")
        async def process_feedback(business_id: str, request: FeedbackRequest):
            """
            Process customer feedback for AI learning
            
            Args:
                business_id: Business identifier
                request: Feedback with rating and optional text
            
            Returns:
                - success: bool
                - learning_result: dict
                - message: str
            """
            try:
                # Pass None (not "") when customer_id absent so orchestrator scoping treats it as unset
                customer_id_val = request.customer_id if request.customer_id else None
                result = self.orchestrator.process_feedback(
                    business_id=business_id,
                    customer_id=customer_id_val,
                    rating=request.rating,
                    feedback_text=request.feedback_text,
                    conversation_id=request.conversation_id,
                    context=request.context
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing feedback: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/escalate")
        async def register_escalation(business_id: str, request: EscalationRequest):
            """
            Register an escalation to human/business owner.
            Backend calls this after detecting escalation_required in chat response.
            Returns escalation_id, recommended_action, and context_for_agent.
            """
            try:
                result = self.orchestrator.register_escalation(
                    business_id=str(business_id),
                    conversation_id=request.conversation_id,
                    customer_id=request.customer_id,
                    reason=request.reason,
                    severity=request.severity,
                    context_summary=request.context_summary,
                    conversation_history=request.conversation_history,
                    customer_message=request.customer_message,
                    ai_response=request.ai_response,
                )
                if not result.get("success"):
                    raise HTTPException(status_code=400, detail=result.get("error"))
                return result
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error registering escalation: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/model-status")
        async def get_model_status(business_id: str):
            """
            Get AI model status for a business
            
            Returns:
                - success: bool
                - business_id: str
                - industry: str
                - model_type: str ('base_model', 'industry_model', 'business_model')
                - model_id: str
                - data_completeness: float
                - last_updated: str (ISO format)
            """
            try:
                result = self.orchestrator.get_model_status(business_id)

                if not result['success']:
                    raise HTTPException(status_code=404, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting model status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/customer/context")
        async def customer_context(body: Dict[str, Any]):
            """
            Return customer context: profile, conversation_history, segments.
            Expects body: { customer_id, business_id, conversation_id (optional), max_history (optional) }
            """
            try:
                business_id = str(body.get("business_id") or "default")
                customer_id = body.get("customer_id")
                conversation_id = body.get("conversation_id")
                max_history = int(body.get("max_history") or 10)

                orchestrator = self.orchestrator

                customer_profile = {}
                conversation_history = []
                segments = []

                # Business profile if available
                business_ai = orchestrator.business_ais.get(business_id)
                if business_ai:
                    profile = business_ai.business_data.get("business_profile") or business_ai.business_data.get("business_info") or {}
                    customer_profile["business_profile"] = profile

                # Find conversation manager
                conv_key = None
                if conversation_id:
                    conv_key = f"{business_id}:conv_{conversation_id}"
                elif customer_id:
                    conv_key = f"{business_id}:cust_{customer_id}"
                else:
                    conv_key = f"{business_id}:default"

                conv_manager = orchestrator.conversation_managers.get(conv_key)
                if conv_manager:
                    # Return recent turns as simple dicts
                    conversation_history = [
                        {"role": t.role, "message": t.message, "timestamp": t.timestamp.isoformat()} for t in conv_manager.conversation_turns[-max_history:]
                    ]
                    if conv_manager.customer_profile:
                        customer_profile["profile"] = conv_manager.customer_profile
                    # Use conversation manager analytics to derive segments
                    analytics = conv_manager.get_conversation_analytics()
                    segments = analytics.get("customer_insights", {}).get("interests", []) if analytics else []

                return {
                    "customer_profile": customer_profile,
                    "conversation_history": conversation_history,
                    "segments": segments
                }
            except Exception as e:
                logger.error(f"Error fetching customer context: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post('/api/v1/kb/retrieve')
        async def kb_retrieve(body: Dict[str, Any]):
            """
            Retrieve KB chunks for a given business/customer and query hint.
            Request body: { business_id, customer_id (optional), trigger_type, query_hint, max_chunks }
            """
            try:
                business_id = str(body.get('business_id') or 'default')
                query_hint = body.get('query_hint') or body.get('trigger_type') or ''
                max_chunks = int(body.get('max_chunks') or 5)

                kb = self.orchestrator.knowledge_base
                if not kb:
                    raise HTTPException(status_code=500, detail='Knowledge base not available')

                resp = kb.retrieve_relevant_knowledge(business_id, query_hint, n_results=max_chunks)
                # Add a simple summary using first chunk(s)
                summary = ''
                confidence = 0.0
                if resp.get('success') and resp.get('documents'):
                    docs = resp.get('documents')
                    summary = docs[0].get('content')[:300]
                    confidence = sum(d.get('relevance_score', 0.0) for d in docs) / max(1, len(docs))

                return {"chunks": resp.get('documents', []), "summary": summary, "confidence": confidence}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in kb_retrieve: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """Run the API server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port, log_level="info")
    
    def get_app(self):
        """Get FastAPI app instance"""
        return self.app


def create_app() -> FastAPI:
    """Create and return FastAPI app instance"""
    api = InferenceAPI()
    return api.get_app()


# For uvicorn: uvicorn api.inference_api:app --reload
app = create_app()


if __name__ == "__main__":
    api = InferenceAPI()
    api.run(port=8000)

