from .base_agent import BaseAgent
from utils.database import DatabaseManager
from utils.response_schema import AgentResponse
from typing import Dict, Any, List
import logging
import datetime

logger = logging.getLogger(__name__)

class FAQAgent(BaseAgent):
    """Specialized agent for handling product and policy questions."""
    
    def __init__(self, api_key: str):
        super().__init__("FAQAgent", api_key)
        self.db = DatabaseManager()
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for FAQ responses."""
        return """You are a knowledgeable customer support specialist. Your role is to:

1. Answer customer questions using the provided FAQ information
2. Be helpful, accurate, and comprehensive
3. If information isn't available, politely acknowledge limitations
4. Suggest contacting support for complex issues

RESPONSE GUIDELINES:
- Use the exact information from FAQ database when available
- Be conversational but professional
- Break down complex information into easy-to-understand points
- Offer additional help when appropriate
- If you can't answer definitively, be honest about limitations

TONE: Friendly, helpful, and professional

When you have relevant FAQ information:
- Provide the complete answer
- Use bullet points or numbering for clarity
- Mention specific product codes when relevant

When information is not available:
- Acknowledge the question
- Explain that you don't have that specific information
- Suggest alternative resources (customer support, website, etc.)
- Offer to help with related questions you can answer"""
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process FAQ query and provide relevant information."""
        try:
            # Extract customer info from context
            customer_id = context.get('customer_id') if context else None
            
            # Search FAQ database
            faq_results = self.db.search_faq(user_input, top_k=3)
            
            if not faq_results:
                # Log the unanswered question
                self._log_faq_interaction(
                    user_input, 
                    "unanswered", 
                    customer_id, 
                    resolved=False
                )
                return self._handle_no_faq_found(user_input)
            
            # Get the best matching FAQ(s)
            best_match = faq_results[0]
            
            # Generate response using AI if available, otherwise use direct FAQ
            if self.client and len(faq_results) > 0:
                result = self._generate_ai_response(user_input, faq_results)
            else:
                result = self._generate_direct_response(user_input, faq_results)
            
            # Log the interaction
            self._log_faq_interaction(
                user_input,
                best_match.get('category', 'general'),
                customer_id,
                resolved=result.get('resolved', False),
                matched_faqs=result.get('matched_faqs', [])
            )
            
            return result
                
        except Exception as e:
            logger.error(f"Error in FAQ processing: {e}")
            # Log the error
            self._log_faq_interaction(
                user_input,
                "error",
                customer_id,
                resolved=False,
                error_message=str(e)
            )
            return AgentResponse(
                response="I apologize, but I'm having trouble accessing our FAQ database right now. Please try again later or contact our customer support team for assistance.",
                resolved=False,
                category="faq",
                needs_followup=True
            ).to_dict()
    
    def _handle_no_faq_found(self, user_input: str) -> Dict[str, Any]:
        """Handle case where no FAQ matches the query."""
        response = """I don't have specific information about your question in our current FAQ database. 

However, I'd be happy to help you in other ways:
• Contact our customer support team for detailed assistance
• Check our website's help section for additional resources
• Let me know if you have other questions I might be able to answer

Is there anything else I can help you with today?"""
        
        return AgentResponse(
            response=response,
            resolved=False,
            category="faq",
            needs_followup=True,
            metadata={
                "faq_found": False,
                "suggested_action": "contact_support"
            }
        ).to_dict()
    
    def _generate_ai_response(self, user_input: str, faq_results: List[Dict]) -> Dict[str, Any]:
        """Generate AI-powered response using FAQ context."""
        try:
            # Prepare FAQ context for AI
            faq_context = "RELEVANT FAQ INFORMATION:\n\n"
            for i, faq in enumerate(faq_results, 1):
                faq_context += f"{i}. Q: {faq['question']}\n"
                faq_context += f"   A: {faq['answer']}\n"
                faq_context += f"   Category: {faq['category']}\n\n"
            
            # Create enhanced prompt with FAQ context
            enhanced_prompt = self.get_system_prompt() + f"\n\n{faq_context}"
            
            # Generate AI response
            ai_response = self.process_with_cache(
                user_input,
                enhanced_prompt
            )
            
            # Determine if question was fully resolved
            resolved = self._assess_resolution_quality(user_input, faq_results, ai_response)
            
            return AgentResponse(
                response=ai_response,
                resolved=resolved,
                category="faq",
                confidence=0.8,
                needs_followup=not resolved,
                metadata={
                    "faq_found": True,
                    "matched_faqs": [faq['id'] for faq in faq_results],
                    "source": "ai_enhanced"
                }
            ).to_dict()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            # Fallback to direct response
            return self._generate_direct_response(user_input, faq_results)
    
    def _generate_direct_response(self, user_input: str, faq_results: List[Dict]) -> Dict[str, Any]:
        """Generate direct response using FAQ information."""
        best_match = faq_results[0]
        
        # Start with the best answer
        response = f"**{best_match['question']}**\n\n{best_match['answer']}"
        
        # Add related information if available
        if len(faq_results) > 1:
            response += "\n\n**Related Information:**\n"
            for faq in faq_results[1:]:
                response += f"• {faq['question']}: {faq['answer'][:100]}{'...' if len(faq['answer']) > 100 else ''}\n"
        
        # Add helpful closing
        response += "\n\nIs there anything else I can help you with regarding this topic?"
        
        return AgentResponse(
            response=response,
            resolved=True,
            category="faq",
            confidence=0.9,
            metadata={
                "faq_found": True,
                "matched_faqs": [faq['id'] for faq in faq_results],
                "source": "direct_faq"
            }
        ).to_dict()
    
    def _assess_resolution_quality(self, user_input: str, faq_results: List[Dict], ai_response: str) -> bool:
        """Assess if the AI response likely resolved the user's question."""
        # Simple heuristics to determine resolution quality
        
        # Check if AI response mentions specific product info, policies, etc.
        resolution_indicators = [
            "specifications", "policy", "days", "warranty", "shipping",
            "payment", "return", "compatible", "dimensions", "price",
            "size", "weight", "material", "color", "model", "version"
        ]
        
        response_lower = ai_response.lower()
        user_lower = user_input.lower()
        
        # If AI response contains specific details, likely resolved
        indicator_count = sum(1 for indicator in resolution_indicators 
                            if indicator in response_lower)
        
        # If response is substantial and contains specifics, consider resolved
        if len(ai_response) > 100 and indicator_count >= 2:
            return True
        
        # If response includes phrases indicating uncertainty, not fully resolved
        uncertainty_phrases = [
            "i don't have", "not available", "contact support", 
            "check our website", "i'm not sure", "unable to find"
        ]
        
        if any(phrase in response_lower for phrase in uncertainty_phrases):
            return False
        
        # Default to resolved if we have good FAQ matches
        return len(faq_results) > 0 and indicator_count > 0
    
    def _log_faq_interaction(self, question: str, category: str, customer_id: str = None, 
                           resolved: bool = True, matched_faqs: List[str] = None, 
                           error_message: str = None):
        """Log FAQ interaction for CRM team analysis."""
        try:
            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'question': question,
                'category': category,
                'customer_id': customer_id or 'anonymous',
                'resolved': resolved,
                'matched_faqs': ','.join(matched_faqs) if matched_faqs else '',
                'error_message': error_message or '',
                'agent_type': 'FAQ'
            }
            
            # Save to database
            # Save to database using existing method
            self.db.log_conversation(
                log_data.get('customer_id', 'anonymous'),
                log_data['question'],
                f"FAQ Category: {log_data['category']} - Resolved: {log_data['resolved']}",
                log_data['category'],
                log_data['resolved'],
                not log_data['resolved']
            )
                        
        except Exception as e:
            logger.error(f"Error logging FAQ interaction: {e}")
    
    def get_available_categories(self) -> List[str]:
        """Get list of available FAQ categories."""
        try:
            faq_data = self.db.get_faq_data()
            categories = set()
            
            # Handle different possible data structures
            if isinstance(faq_data, dict) and "records" in faq_data:
                records = faq_data["records"]
            elif isinstance(faq_data, list):
                records = faq_data
            else:
                records = []
            
            for record in records:
                categories.add(record.get("category", "general"))
                
            return sorted(list(categories))
        except Exception as e:
            logger.error(f"Error getting FAQ categories: {e}")
            return ["general", "product_info", "shipping", "warranty", "returns"]
    
    def get_faq_by_category(self, category: str) -> List[Dict]:
        """Get FAQ items by category."""
        try:
            faq_data = self.db.get_faq_data()
            
            # Handle different possible data structures
            if isinstance(faq_data, dict) and "records" in faq_data:
                records = faq_data["records"]
            elif isinstance(faq_data, list):
                records = faq_data
            else:
                records = []
            
            return [
                record for record in records
                if record.get("category", "general").lower() == category.lower()
            ]
        except Exception as e:
            logger.error(f"Error getting FAQ by category {category}: {e}")
            return []
    
    def search_faq_by_keywords(self, keywords: List[str], category: str = None) -> List[Dict]:
        """Search FAQ by specific keywords with optional category filter."""
        try:
            faq_data = self.db.get_faq_data()
            
            # Handle different possible data structures
            if isinstance(faq_data, dict) and "records" in faq_data:
                records = faq_data["records"]
            elif isinstance(faq_data, list):
                records = faq_data
            else:
                records = []
            
            results = []
            
            for record in records:
                # Category filter
                if category and record.get("category", "general").lower() != category.lower():
                    continue
                
                # Keyword matching
                question_lower = record.get("question", "").lower()
                answer_lower = record.get("answer", "").lower()
                
                # Check if any keyword matches
                keyword_matches = sum(
                    1 for keyword in keywords
                    if keyword.lower() in question_lower or keyword.lower() in answer_lower
                )
                
                if keyword_matches > 0:
                    record['relevance_score'] = keyword_matches / len(keywords)
                    results.append(record)
            
            # Sort by relevance score
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAQ by keywords: {e}")
            return []
    
    def get_popular_questions(self, limit: int = 5) -> List[Dict]:
        """Get most popular FAQ questions based on interaction logs."""
        try:
            # This would require analyzing the logs database
            # For now, return a basic implementation
            faq_data = self.db.get_faq_data()
            
            if isinstance(faq_data, dict) and "records" in faq_data:
                records = faq_data["records"]
            elif isinstance(faq_data, list):
                records = faq_data
            else:
                records = []
            
            # Return first N items (in a real implementation, you'd sort by popularity)
            return records[:limit]
            
        except Exception as e:
            logger.error(f"Error getting popular questions: {e}")
            return []