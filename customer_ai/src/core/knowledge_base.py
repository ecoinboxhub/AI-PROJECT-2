"""
Knowledge Base Manager - Indexes and retrieves business knowledge for RAG
Automatically creates embeddings from business data
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manages business knowledge base for RAG
    Indexes FAQs, products, services, policies, and conversation history
    """
    
    def __init__(self, storage_mode: str = "pgvector"):
        """
        Initialize knowledge base manager
        
        Args:
            storage_mode: 'pgvector' for PostgreSQL with pgvector (default, recommended for production),
                         'local' for ChromaDB (development only)
        """
        self.vector_store = get_vector_store(storage_mode)
        self.storage_mode = storage_mode
    
    def index_business_data(self, business_id: str, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index all business data for RAG retrieval
        
        Args:
            business_id: Unique identifier for the business
            business_data: Complete business information (knowledge_data format)
            
        Returns:
            Indexing results with statistics
        """
        try:
            documents = []
            metadatas = []
            ids = []
            
            # Handle new knowledge_data structure
            if 'business_info' in business_data:
                # New structure: knowledge_data format
                profile_docs = self._index_business_info(business_data.get('business_info', {}))
                documents.extend(profile_docs['documents'])
                metadatas.extend(profile_docs['metadatas'])
                ids.extend(profile_docs['ids'])
                
                # Index products (separate from services in new structure)
                product_docs = self._index_products_services(business_data.get('products', []))
                documents.extend(product_docs['documents'])
                metadatas.extend(product_docs['metadatas'])
                ids.extend(product_docs['ids'])
                
                # Index services (separate array in new structure)
                service_docs = self._index_products_services(business_data.get('services', []), item_type="service")
                documents.extend(service_docs['documents'])
                metadatas.extend(service_docs['metadatas'])
                ids.extend(service_docs['ids'])
                
                # Index business hours
                if 'business_hours' in business_data:
                    hours_docs = self._index_business_hours(business_data['business_hours'])
                    documents.extend(hours_docs['documents'])
                    metadatas.extend(hours_docs['metadatas'])
                    ids.extend(hours_docs['ids'])
                
                # Index policies
                if 'policies' in business_data:
                    policy_docs = self._index_policies(business_data['policies'])
                    documents.extend(policy_docs['documents'])
                    metadatas.extend(policy_docs['metadatas'])
                    ids.extend(policy_docs['ids'])
                
            elif 'business_profile' in business_data:
                # Legacy structure: backward compatibility
                profile_docs = self._index_business_profile(business_data.get('business_profile', {}))
                documents.extend(profile_docs['documents'])
                metadatas.extend(profile_docs['metadatas'])
                ids.extend(profile_docs['ids'])
                
                # Index products/services (legacy combined array)
                product_docs = self._index_products_services(business_data.get('products_services', []))
                documents.extend(product_docs['documents'])
                metadatas.extend(product_docs['metadatas'])
                ids.extend(product_docs['ids'])
            
            # Index FAQs (same in both structures)
            if 'faqs' in business_data:
                faq_docs = self._index_faqs(business_data['faqs'])
                documents.extend(faq_docs['documents'])
                metadatas.extend(faq_docs['metadatas'])
                ids.extend(faq_docs['ids'])
            
            # Index AI context (legacy support)
            if 'ai_context' in business_data:
                context_docs = self._index_ai_context(business_data['ai_context'])
                documents.extend(context_docs['documents'])
                metadatas.extend(context_docs['metadatas'])
                ids.extend(context_docs['ids'])
            
            # Index industry-specific data (legacy support)
            if 'industry_data' in business_data:
                industry_docs = self._index_industry_data(business_data['industry_data'])
                documents.extend(industry_docs['documents'])
                metadatas.extend(industry_docs['metadatas'])
                ids.extend(industry_docs['ids'])
            
            # Make IDs unique by prefixing with business_id
            unique_ids = [f"{business_id}_{id}" for id in ids]
            
            # Add all documents to vector store
            success = self.vector_store.add_documents(
                business_id=business_id,
                documents=documents,
                metadatas=metadatas,
                ids=unique_ids
            )
            
            if success:
                logger.info(f"Successfully indexed {len(documents)} documents for {business_id}")
                return {
                    "success": True,
                    "documents_indexed": len(documents),
                    "business_id": business_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add documents to vector store"
                }
            
        except Exception as e:
            logger.error(f"Error indexing business data for {business_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _index_business_info(self, business_info: Dict[str, Any]) -> Dict[str, List]:
        """Index business info from new knowledge_data structure"""
        documents = []
        metadatas = []
        ids = []
        
        # Main business description
        business_name = business_info.get('name', 'Unknown')
        description = business_info.get('description', '')
        
        if description:
            documents.append(
                f"Business: {business_name}\n"
                f"Description: {description}"
            )
            metadatas.append({
                "type": "business_info",
                "source": "description",
                "business_name": business_name
            })
            ids.append("business_info_main")
        
        # Contact information
        contact_text = "Contact Information:\n"
        has_contact = False
        
        if business_info.get('phone'):
            contact_text += f"Phone: {business_info['phone']}\n"
            has_contact = True
        if business_info.get('email'):
            contact_text += f"Email: {business_info['email']}\n"
            has_contact = True
        if business_info.get('address'):
            contact_text += f"Address: {business_info['address']}\n"
            has_contact = True
        if business_info.get('whatsapp_number'):
            contact_text += f"WhatsApp: {business_info['whatsapp_number']}\n"
            has_contact = True
        if business_info.get('timezone'):
            contact_text += f"Timezone: {business_info['timezone']}\n"
            has_contact = True
        
        if has_contact:
            documents.append(contact_text)
            metadatas.append({
                "type": "contact_info",
                "source": "business_info"
            })
            ids.append("business_info_contact")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_business_profile(self, profile: Dict[str, Any]) -> Dict[str, List]:
        """Index business profile information (legacy format)"""
        documents = []
        metadatas = []
        ids = []
        
        # Main business description
        if profile.get('description'):
            documents.append(
                f"Business: {profile.get('business_name', 'Unknown')}\n"
                f"Description: {profile['description']}\n"
                f"Industry: {profile.get('industry', 'General')}"
            )
            metadatas.append({
                "type": "business_profile",
                "source": "description",
                "business_name": profile.get('business_name', '')
            })
            ids.append("profile_main")
        
        # Contact information
        if profile.get('contact_info'):
            contact = profile['contact_info']
            contact_text = "Contact Information:\n"
            if contact.get('phone'):
                contact_text += f"Phone: {contact['phone']}\n"
            if contact.get('email'):
                contact_text += f"Email: {contact['email']}\n"
            if contact.get('address'):
                contact_text += f"Address: {contact['address']}\n"
            
            documents.append(contact_text)
            metadatas.append({
                "type": "contact_info",
                "source": "business_profile"
            })
            ids.append("profile_contact")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_products_services(self, items: List[Dict[str, Any]], item_type: str = "product") -> Dict[str, List]:
        """Index products and services"""
        documents = []
        metadatas = []
        ids = []
        
        for idx, item in enumerate(items):
            # Create detailed product/service document
            item_name = item.get('name', 'Unknown')
            doc_text = f"{item_type.capitalize()}: {item_name}\n"
            
            # Add description if available
            description = item.get('description', '')
            if description:
                doc_text += f"Description: {description}\n"
            else:
                doc_text += "Description: No description provided\n"
            
            if 'price' in item:
                doc_text += f"Price: ${item['price']}\n"
            if 'category' in item:
                doc_text += f"Category: {item['category']}\n"
            if 'availability' in item:
                doc_text += f"Availability: {'Available' if item['availability'] else 'Not Available'}\n"
            
            documents.append(doc_text)
            metadatas.append({
                "type": item_type,
                "name": item_name,
                "price": item.get('price', 0),
                "category": item.get('category', ''),
                "availability": item.get('availability', True),
                "id": item.get('id', f"{item_type}_{idx}")
            })
            ids.append(f"{item_type}_{idx}")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_business_hours(self, business_hours: Dict[str, Any]) -> Dict[str, List]:
        """Index business hours"""
        documents = []
        metadatas = []
        ids = []
        
        hours_text = "Business Hours:\n"
        for day, hours_info in business_hours.items():
            if isinstance(hours_info, dict):
                if hours_info.get('is_closed', False):
                    hours_text += f"{day.capitalize()}: Closed\n"
                else:
                    open_time = hours_info.get('open', '')
                    close_time = hours_info.get('close', '')
                    if open_time and close_time:
                        hours_text += f"{day.capitalize()}: {open_time} - {close_time}\n"
            elif isinstance(hours_info, str):
                hours_text += f"{day.capitalize()}: {hours_info}\n"
        
        if hours_text != "Business Hours:\n":
            documents.append(hours_text)
            metadatas.append({
                "type": "business_hours",
                "source": "business_info"
            })
            ids.append("business_hours_main")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_policies(self, policies: Dict[str, Any]) -> Dict[str, List]:
        """Index business policies"""
        documents = []
        metadatas = []
        ids = []
        
        if policies.get('return_policy'):
            documents.append(f"Return Policy: {policies['return_policy']}")
            metadatas.append({
                "type": "policy",
                "policy_type": "return_policy"
            })
            ids.append("policy_return")
        
        if policies.get('shipping_policy'):
            documents.append(f"Shipping Policy: {policies['shipping_policy']}")
            metadatas.append({
                "type": "policy",
                "policy_type": "shipping_policy"
            })
            ids.append("policy_shipping")
        
        if policies.get('payment_methods'):
            documents.append(f"Payment Methods: {policies['payment_methods']}")
            metadatas.append({
                "type": "policy",
                "policy_type": "payment_methods"
            })
            ids.append("policy_payment")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_faqs(self, faqs: List[Dict[str, str]]) -> Dict[str, List]:
        """Index FAQs"""
        documents = []
        metadatas = []
        ids = []
        
        for idx, faq in enumerate(faqs):
            doc_text = f"Question: {faq.get('question', '')}\n"
            doc_text += f"Answer: {faq.get('answer', '')}"
            
            documents.append(doc_text)
            metadatas.append({
                "type": "faq",
                "question": faq.get('question', ''),
                "source": "faqs"
            })
            ids.append(f"faq_{idx}")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_ai_context(self, ai_context: Dict[str, Any]) -> Dict[str, List]:
        """Index AI context information"""
        documents = []
        metadatas = []
        ids = []
        
        # Index customer personas
        if 'customer_personas' in ai_context:
            for idx, persona in enumerate(ai_context['customer_personas']):
                doc_text = f"Customer Persona: {persona.get('type', 'Unknown')}\n"
                doc_text += f"Characteristics: {persona.get('characteristics', '')}\n"
                doc_text += f"Needs: {persona.get('needs', '')}\n"
                doc_text += f"Approach: {persona.get('approach', '')}"
                
                documents.append(doc_text)
                metadatas.append({
                    "type": "customer_persona",
                    "persona_type": persona.get('type', '')
                })
                ids.append(f"persona_{idx}")
        
        # Index business positioning
        if 'business_positioning' in ai_context:
            documents.append(f"Business Positioning:\n{ai_context['business_positioning']}")
            metadatas.append({"type": "business_positioning"})
            ids.append("positioning_main")
        
        # Index value propositions
        if 'value_propositions' in ai_context:
            for idx, vp in enumerate(ai_context['value_propositions']):
                documents.append(f"Value Proposition: {vp}")
                metadatas.append({"type": "value_proposition"})
                ids.append(f"value_prop_{idx}")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def _index_industry_data(self, industry_data: Dict[str, Any]) -> Dict[str, List]:
        """Index industry-specific data"""
        documents = []
        metadatas = []
        ids = []
        
        # This can be extended based on industry-specific needs
        for key, value in industry_data.items():
            if isinstance(value, str):
                documents.append(f"{key}: {value}")
                metadatas.append({"type": "industry_data", "field": key})
                ids.append(f"industry_{key}")
        
        return {"documents": documents, "metadatas": metadatas, "ids": ids}
    
    def retrieve_relevant_knowledge(
        self, 
        business_id: str, 
        query: str, 
        n_results: int = 5,
        filter_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant knowledge for a query
        
        Args:
            business_id: Unique identifier for the business
            query: User query or message
            n_results: Number of results to return
            filter_type: Optional filter by document type
            
        Returns:
            Retrieved documents with relevance scores
        """
        try:
            # Build metadata filter if needed
            where = {"type": filter_type} if filter_type else None
            
            # Query vector store
            results = self.vector_store.query(
                business_id=business_id,
                query_text=query,
                n_results=n_results,
                where=where
            )
            
            # Format results
            retrieved_docs = []
            for doc, metadata, distance in zip(
                results['documents'], 
                results['metadatas'], 
                results['distances']
            ):
                retrieved_docs.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance,  # Convert distance to similarity
                    "distance": distance
                })
            
            return {
                "success": True,
                "documents": retrieved_docs,
                "count": len(retrieved_docs)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge for {business_id}: {e}")
            return {
                "success": False,
                "documents": [],
                "count": 0,
                "error": str(e)
            }
    
    def add_conversation_to_knowledge(
        self, 
        business_id: str, 
        customer_message: str, 
        ai_response: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add conversation exchange to knowledge base for future reference
        
        Args:
            business_id: Unique identifier for the business
            customer_message: Customer's message
            ai_response: AI's response
            metadata: Optional metadata (intent, sentiment, etc.)
            
        Returns:
            Success status
        """
        try:
            doc_text = f"Customer: {customer_message}\nAI Response: {ai_response}"
            
            conversation_metadata = {
                "type": "conversation",
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            doc_id = f"conv_{datetime.now().timestamp()}"
            
            success = self.vector_store.add_documents(
                business_id=business_id,
                documents=[doc_text],
                metadatas=[conversation_metadata],
                ids=[f"{business_id}_{doc_id}"]
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding conversation to knowledge base: {e}")
            return False
    
    def update_knowledge(
        self, 
        business_id: str, 
        doc_id: str, 
        new_content: str, 
        new_metadata: Dict[str, Any]
    ) -> bool:
        """
        Update existing knowledge base entry
        
        Args:
            business_id: Unique identifier for the business
            doc_id: Document ID to update
            new_content: New document content
            new_metadata: New metadata
            
        Returns:
            Success status
        """
        return self.vector_store.update_document(
            business_id=business_id,
            doc_id=f"{business_id}_{doc_id}",
            document=new_content,
            metadata=new_metadata
        )
    
    def delete_knowledge(self, business_id: str, doc_ids: List[str]) -> bool:
        """
        Delete knowledge base entries
        
        Args:
            business_id: Unique identifier for the business
            doc_ids: List of document IDs to delete
            
        Returns:
            Success status
        """
        unique_ids = [f"{business_id}_{doc_id}" for doc_id in doc_ids]
        return self.vector_store.delete_documents(business_id, unique_ids)
    
    def get_knowledge_stats(self, business_id: str) -> Dict[str, Any]:
        """
        Get statistics about business knowledge base
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            Knowledge base statistics
        """
        return self.vector_store.get_collection_stats(business_id)


def get_knowledge_base(storage_mode: Optional[str] = None) -> KnowledgeBaseManager:
    """
    Factory function to get knowledge base manager
    
    Args:
        storage_mode: 'pgvector' for PostgreSQL with pgvector (default, recommended for production),
                     'local' for ChromaDB (development only).
                     If None, reads from VECTOR_STORAGE_MODE environment variable (defaults to 'pgvector')
        
    Returns:
        KnowledgeBaseManager instance
    """
    import os
    if storage_mode is None:
        storage_mode = os.getenv('VECTOR_STORAGE_MODE', 'pgvector')
    
    return KnowledgeBaseManager(storage_mode=storage_mode)

