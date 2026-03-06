"""
Business Owner AI - Minimal Inference API
Clean AI inference endpoints for business intelligence
"""

import logging
import os
import uuid
import requests
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.business_intelligence import get_business_intelligence
from ..core.trigger_detector import classify_trigger
from ..core.orchestrator import orchestrate_outbound

logger = logging.getLogger(__name__)


# Pydantic models
class ChatRequest(BaseModel):
    query: str = Field(..., description="Business owner query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class SalesAnalysisRequest(BaseModel):
    conversations: List[Dict[str, Any]] = Field(..., description="Conversation data")
    sales_data: Optional[List[Dict[str, Any]]] = Field(None, description="Sales transaction data")
    time_period: str = Field('last_30_days', description="Analysis period")


class SegmentCustomersRequest(BaseModel):
    customer_data: List[Dict[str, Any]] = Field(..., description="Customer profiles")
    method: str = Field('behavior', description="Segmentation method")


class BroadcastRequest(BaseModel):
    message_intent: str = Field(..., description="Message purpose")
    target_segment: str = Field(..., description="Target customer segment")
    business_data: Dict[str, Any] = Field(..., description="Business information")
    personalization_data: Optional[Dict[str, Any]] = None


class BusinessOwnerInferenceAPI:
    """Minimal inference API for Business Owner AI"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ndara.ai Business Owner AI - Inference API",
            description="AI inference endpoints for business intelligence",
            version="1.0.0"
        )
        
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Business Owner AI Inference API initialized")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "ndara.ai Business Owner AI",
                "version": "1.0.0",
                "status": "operational",
                "docs": "/docs"
            }
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/api/v1/chat")
        async def chat(business_id: str, industry: str, request: ChatRequest):
            """
            Process business owner query
            
            This is the main chat endpoint that handles all business intelligence queries including:
            - Sales analysis (e.g., "How are my sales performing?")
            - Customer segmentation (e.g., "Segment my customers")
            - Inventory retrieval/search (e.g., "Show me low stock items", "What products are out of stock?")
            - Invoice retrieval/search (e.g., "Show me unpaid invoices", "Find invoice INV-123")
            - Broadcast message preparation
            - General business intelligence queries
            
            
            Returns AI-generated business intelligence response with parsed query and guidance
            """
            try:
                bi = get_business_intelligence(business_id, industry)
                result = await bi.process_query(request.query, request.context or {})
                return result
            except Exception as e:
                logger.error(f"Error in chat: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/analyze-sales")
        async def analyze_sales(business_id: str, request: SalesAnalysisRequest):
            """
            Analyze sales performance
            
            Returns:
                - key_metrics: Sales KPIs
                - trends: Performance trends
                - insights: Actionable insights
                - recommendations: Strategic recommendations
            """
            try:
                from ..core.sales_analyzer import get_sales_analyzer
                analyzer = get_sales_analyzer(business_id)
                
                analysis = analyzer.analyze_sales_performance(
                    request.conversations,
                    request.sales_data,
                    request.time_period
                )
                
                return {
                    "success": True,
                    "analysis": analysis
                }
            except Exception as e:
                logger.error(f"Error analyzing sales: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/segment-customers")
        async def segment_customers(business_id: str, request: SegmentCustomersRequest):
            """
            Segment customers using ML
            
            Returns:
                - segments: Customer groups
                - segment_profiles: Characteristics of each segment
                - recommendations: Targeted strategies
            """
            try:
                from ..core.customer_segmentation import get_customer_segmentation
                segmenter = get_customer_segmentation(business_id)
                
                segmentation = segmenter.segment_customers(
                    request.customer_data,
                    request.method
                )
                
                return {
                    "success": True,
                    "segmentation": segmentation
                }
            except Exception as e:
                logger.error(f"Error segmenting customers: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/prepare-broadcast")
        async def prepare_broadcast(business_id: str, request: BroadcastRequest):
            """
            Prepare broadcast message
            
            Returns:
                - primary_message: Main message
                - variants: A/B test variants
                - call_to_action: Recommended CTA
                - recommended_send_time: Optimal timing
            """
            try:
                from ..core.broadcast_composer import get_broadcast_composer
                composer = get_broadcast_composer(business_id)
                
                broadcast = composer.compose_broadcast(
                    request.message_intent,
                    request.target_segment,
                    request.business_data,
                    request.personalization_data
                )
                
                return broadcast
            except Exception as e:
                logger.error(f"Error preparing broadcast: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/competitive-insights")
        async def competitive_insights(
            business_id: str,
            industry: str,
            business_data: Dict[str, Any],
            similar_businesses: Optional[List[Dict[str, Any]]] = None
        ):
            """
            Generate competitive intelligence
            
            Returns:
                - swot_analysis: Strengths, weaknesses, opportunities, threats
                - market_trends: Industry trends
                - competitive_advantages: Key differentiators
                - recommendations: Strategic recommendations
            """
            try:
                from ..core.competitive_intelligence import get_competitive_intelligence
                ci = get_competitive_intelligence(business_id, industry)
                
                analysis = ci.analyze_competitive_position(
                    business_data,
                    similar_businesses
                )
                
                return {
                    "success": True,
                    "analysis": analysis
                }
            except Exception as e:
                logger.error(f"Error generating competitive insights: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/orchestrator/triggers")
        async def receive_trigger(payload: Dict[str, Any]):
            """
            Receive a trigger event, classify it, and run orchestration to produce
            a message_content ready for downstream delivery.
            """
            try:
                # Classify/normalize
                trigger = classify_trigger(payload)

                # Orchestrate
                orchestration = orchestrate_outbound(trigger)

                # Optionally, attach trigger echo for traceability
                orchestration["trigger"] = trigger

                return orchestration
            except Exception as e:
                logger.error(f"Error receiving trigger: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/outbound-call")
        async def request_outbound_call(request: Dict[str, Any]):
            """
            Request an outbound call to a customer
            
            This endpoint initiates the outbound call workflow:
            1. Validates customer phone number exists
            2. Checks call cooldown period
            3. Retrieves customer context from Customer AI
            4. Fetches relevant knowledge base information
            5. Creates call context for Voice Agent
            6. Triggers outbound call via Voice Agent
            
            Request Body:
                customer_id: Unique customer identifier
                phone_number: Customer's phone number (with country code)
                business_id: Business identifier
                call_purpose: Why the call is being made
                campaign_id: Optional campaign identifier
                call_type: Type of call (default: outbound)
                conversation_goal: Primary goal of conversation
            
            Returns:
                call_id: Unique identifier for tracking the call
                status: Current call status
                call_context: Context packaged for Voice Agent
                message: Human-readable status message
            """
            try:
                import uuid
                import requests
                
                from ..core.outbound_call_orchestrator import (
                    create_call_context,
                    store_call_state,
                    check_call_cooldown,
                    get_call_state
                )
                
                customer_id = request.get("customer_id")
                phone_number = request.get("phone_number")
                business_id = request.get("business_id")
                call_purpose = request.get("call_purpose")
                campaign_id = request.get("campaign_id")
                call_type = request.get("call_type", "outbound")
                conversation_goal = request.get("conversation_goal", "inform")
                
                # Validate required fields
                if not all([customer_id, phone_number, business_id, call_purpose]):
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required fields: customer_id, phone_number, business_id, call_purpose"
                    )
                
                # Check if customer has a valid phone number
                if not phone_number or len(str(phone_number).strip()) < 8:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid phone number. Must be at least 8 digits."
                    )
                
                # Check call cooldown (don't call same customer too frequently)
                if not check_call_cooldown(customer_id, business_id, cooldown_hours=24):
                    raise HTTPException(
                        status_code=400,
                        detail="Customer has been called within the last 24 hours. Please wait before calling again."
                    )
                
                # Create unique call ID
                call_id = f"call_{uuid.uuid4().hex[:12]}"
                
                # Store initial call state
                store_call_state(call_id, {
                    "call_id": call_id,
                    "customer_id": customer_id,
                    "business_id": business_id,
                    "phone_number": phone_number,
                    "call_purpose": call_purpose,
                    "campaign_id": campaign_id,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                })
                
                # Fetch customer context from Customer AI
                try:
                    customer_ai_base = "http://localhost:8000"
                    ctx_payload = {
                        "customer_id": customer_id,
                        "business_id": business_id
                    }
                    
                    resp = requests.post(
                        f"{customer_ai_base}/api/v1/customer/context",
                        json=ctx_payload,
                        timeout=30
                    )
                    
                    if resp.status_code == 200:
                        customer_context = resp.json()
                    else:
                        customer_context = {}
                except Exception as e:
                    logger.warning(f"Failed to fetch customer context: {str(e)}")
                    customer_context = {}
                
                # Fetch business name from context
                business_name = (customer_context.get("customer_profile", {})
                                .get("business_profile", {})
                                .get("business_name", business_id))
                
                # Create call context
                call_context = create_call_context(
                    customer_id=customer_id,
                    phone_number=phone_number,
                    business_id=business_id,
                    business_name=business_name,
                    call_purpose=call_purpose,
                    call_type=call_type,
                    campaign_id=campaign_id,
                    conversation_goal=conversation_goal
                )
                
                # Update call state with context
                store_call_state(call_id, {
                    "status": "context_prepared",
                    "call_context": call_context,
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                # Return response with call ID and context
                return {
                    "success": True,
                    "call_id": call_id,
                    "status": "context_prepared",
                    "message": f"Outbound call prepared for {phone_number}. Call context created.",
                    "call_context": call_context
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error requesting outbound call: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/outbound-call/start")
        async def start_outbound_call(request: Dict[str, Any]):
            """
            Start an outbound call using Voice Agent
            
            This endpoint triggers the actual outbound call after context has been prepared.
            It sends the call context to the Voice Agent which will:
            1. Dial the customer
            2. Play the greeting
            3. Conduct the conversation using knowledge base context
            4. Track call progress
            
            Request Body:
                call_id: The call ID from request_outbound_call
                business_name: Display name of business (required for greeting)
            
            Returns:
                session_id: Voice Agent session identifier
                status: Call started status
                message: Human-readable status message
            """
            try:
                import requests
                
                from ..core.outbound_call_orchestrator import (
                    get_call_state,
                    update_call_state
                )
                
                call_id = request.get("call_id")
                business_name = request.get("business_name")
                
                if not call_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing required field: call_id"
                    )
                
                # Get call state
                call_state = get_call_state(call_id)
                if not call_state:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Call not found: {call_id}"
                    )
                
                # Update call state to dialing
                update_call_state(call_id, {
                    "status": "dialing",
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                # Call Voice Agent to start the outbound call
                try:
                    voice_agent_base = "http://localhost:8003"
                    
                    voice_payload = {
                        "trigger_id": call_id,
                        "trigger_type": "outbound_call",
                        "business_id": call_state.get("business_id"),
                        "business_name": business_name or call_state.get("business_id"),
                        "customer_id": call_state.get("customer_id"),
                        "message_content": call_state.get("call_context", {}).get("call_purpose", ""),
                        "personalization": {
                            "first_name": call_state.get("customer_id", "").split("_")[-1] if "_" in call_state.get("customer_id", "") else "Customer"
                        },
                        "tts_options": {"format": "MP3"}
                    }
                    
                    resp = requests.post(
                        f"{voice_agent_base}/api/v1/outbound/session-prepare",
                        json=voice_payload,
                        timeout=30
                    )
                    
                    if resp.status_code != 200:
                        update_call_state(call_id, {
                            "status": "failed",
                            "error": f"Voice Agent returned status {resp.status_code}",
                            "updated_at": datetime.utcnow().isoformat()
                        })
                        raise HTTPException(
                            status_code=500,
                            detail=f"Voice Agent failed: {resp.text}"
                        )
                    
                    voice_response = resp.json()
                    session_id = voice_response.get("session_id")
                    
                    # Update call state with session info
                    update_call_state(call_id, {
                        "status": "in_progress",
                        "session_id": session_id,
                        "updated_at": datetime.utcnow().isoformat()
                    })
                    
                    return {
                        "success": True,
                        "call_id": call_id,
                        "session_id": session_id,
                        "status": "in_progress",
                        "message": f"Outbound call started. Session: {session_id}"
                    }
                    
                except requests.exceptions.RequestException as e:
                    update_call_state(call_id, {
                        "status": "failed",
                        "error": str(e),
                        "updated_at": datetime.utcnow().isoformat()
                    })
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to start call with Voice Agent: {str(e)}"
                    )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error starting outbound call: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/outbound-call/{call_id}/status")
        async def get_outbound_call_status(call_id: str):
            """
            Get the current status of an outbound call
            
            Returns:
                call_id: The call identifier
                status: Current call state
                details: Additional call information
                timestamp: Last update time
            """
            try:
                from ..core.outbound_call_orchestrator import get_call_state
                
                call_state = get_call_state(call_id)
                if not call_state:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Call not found: {call_id}"
                    )
                
                return {
                    "success": True,
                    "call_id": call_id,
                    "status": call_state.get("status"),
                    "details": {
                        "customer_id": call_state.get("customer_id"),
                        "business_id": call_state.get("business_id"),
                        "phone_number": call_state.get("phone_number"),
                        "call_purpose": call_state.get("call_purpose"),
                        "campaign_id": call_state.get("campaign_id"),
                        "session_id": call_state.get("session_id"),
                        "created_at": call_state.get("created_at"),
                        "updated_at": call_state.get("updated_at")
                    }
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting call status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/outbound-call/results")
        async def get_outbound_call_results(
            customer_id: Optional[str] = None,
            business_id: Optional[str] = None,
            limit: int = 100
        ):
            """
            Get call results with optional filtering
            
            Returns:
                results: List of call results
                total: Total number of results
            """
            try:
                from ..core.outbound_call_orchestrator import get_all_call_results
                
                results = get_all_call_results(
                    customer_id=customer_id,
                    business_id=business_id,
                    limit=limit
                )
                
                return {
                    "success": True,
                    "results": results,
                    "total": len(results)
                }
                
            except Exception as e:
                logger.error(f"Error getting call results: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: str = '0.0.0.0', port: int = 8001):
        """Run the API server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port, log_level="info")
    
    def get_app(self):
        """Get FastAPI app instance"""
        return self.app


def create_app() -> FastAPI:
    """Create and return FastAPI app instance"""
    api = BusinessOwnerInferenceAPI()
    return api.get_app()


# For uvicorn
app = create_app()


if __name__ == "__main__":
    api = BusinessOwnerInferenceAPI()
    api.run(port=8001)
