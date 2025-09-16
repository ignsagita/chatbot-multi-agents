from .base_agent import BaseAgent
from utils.validators import InputValidator
from utils.response_schema import AgentResponse
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TriageAgent(BaseAgent):
    """Triage agent that classifies and routes customer queries"""
    
    def __init__(self, api_key: str):
        super().__init__("TriageAgent", api_key)
        self.validator = InputValidator()
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for triage classification"""
        return """You are a customer support triage specialist. Your job is to classify customer queries into these categories:

CATEGORIES:
1. "refund" - Customer wants to return a product or get money back
2. "faq" - Customer has questions about products, policies, shipping, etc.
3. "other" - Queries that don't fit the above categories

INSTRUCTIONS:
- Analyze the customer's message carefully
- Classify into ONE category only, calculate your confidence level
- For refund requests, check if they mention invoice numbers (INV####) and customer IDs (CUST###)
- For FAQ questions, identify if it's about products, policies, or general information
- Be concise and professional

RESPONSE FORMAT:
Category: [category]
Confidence: [high/medium/low]
Reasoning: [brief explanation]
Next Action: [what should happen next]

Examples:
- "I want to return my headphones" --> Category: refund
- "What's your return policy?" --> Category: faq
- "Hello, how are you?" --> Category: other"""
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process and classify the user input"""
        try:
            # Validate input
            is_valid, error_msg = self.validator.validate_query_input(user_input)
            if not is_valid:
                return {
                    "category": "other",
                    "response": error_msg,
                    "confidence": "high",
                    "needs_routing": False,
                    "resolved": False
                }
            
            # Sanitize input
            sanitized_input = self.validator.sanitize_input(user_input)
            
            # Use rule-based classification as fallback
            rule_based_category = self.validator.classify_query_intent(sanitized_input)
            
            # Get AI classification if API key is available
            if self.client:
                ai_response = self.process_with_cache(
                    sanitized_input, 
                    self.get_system_prompt()
                )
                
                # Parse AI response
                parsed_result = self._parse_ai_response(ai_response)
                
                # Validate AI classification with rule-based fallback
                final_category = self._validate_classification(
                    parsed_result.get("category", rule_based_category),
                    rule_based_category,
                    sanitized_input
                )
            else:
                # Use rule-based classification only
                final_category = rule_based_category
                parsed_result = {
                    "reasoning": "Rule-based classification (API not available)",
                    "confidence": "medium"
                }
            
            # Check for complete refund information
            has_complete_refund_info = self.validator.is_complete_refund_request(sanitized_input)
            
            # Determine routing and response
            result = self._build_response(
                final_category, 
                sanitized_input,
                parsed_result,
                has_complete_refund_info
            )
            
            logger.info(f"Triage classified query as: {final_category}")
            return result
            
        except Exception as e:
            logger.error(f"Error in triage processing: {e}")
            return {
                "category": "other",
                "response": "I'm sorry, I'm having trouble processing your request. Please try again.",
                "confidence": "low",
                "needs_routing": False,
                "resolved": False
            }
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, str]:
        """Parse the AI response into structured data"""
        result = {}
        
        for line in ai_response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'category':
                    result['category'] = value.lower()
                elif key == 'confidence':
                    result['confidence'] = value.lower()
                elif key == 'reasoning':
                    result['reasoning'] = value
                elif key == 'next action':
                    result['next_action'] = value
        
        return result
    
    def _validate_classification(self, ai_category: str, rule_category: str, user_input: str) -> str:
        """Validate AI classification against rule-based classification"""
        valid_categories = ["refund", "faq", "partnership", "other"]
        
        # Ensure AI category is valid
        if ai_category not in valid_categories:
            return rule_category
        
        # For critical categories, prefer rule-based if there's disagreement
        if rule_category == "refund" and ai_category != "refund":
            # Check for clear refund indicators
            refund_keywords = ["refund", "return", "money back", "cancel", "invoice"]
            if any(keyword in user_input.lower() for keyword in refund_keywords):
                return "refund"
        
        return ai_category
    
    def _build_response(self, category: str, user_input: str, parsed_result: Dict, 
                       has_complete_refund_info: bool) -> Dict[str, Any]:
        """Build the final response based on classification"""
        
        if category == "refund":
            if has_complete_refund_info:
                return AgentResponse(
                    response="I can help you with your refund request...",
                    resolved=False,
                    category="refund",
                    confidence=self._normalize_confidence(parsed_result.get("confidence", "high")),
                    needs_followup=True,
                    metadata={"extracted_info": self.validator.extract_transaction_info(user_input)}
                )
            else:
                return {
                    "category": "refund",
                    "response": "I'd be happy to help with your refund request. Please provide your Invoice Number (format: INV####) and Customer ID (format: CUST###) so I can look up your transaction.",
                    "confidence": parsed_result.get("confidence", "medium"),
                    "needs_routing": False,
                    "resolved": False,
                    "needs_more_info": True
                }
        
        elif category == "faq":
            return {
                "category": "faq",
                "response": "I'll help you find the information you're looking for. Let me search our knowledge base for you.",
                "confidence": parsed_result.get("confidence", "high"),
                "needs_routing": True,
                "resolved": False
            }
        
        else:  # other
            return {
                "category": "other",
                "response": "Thank you for contacting us! I'd be happy to help you. Could you please provide more specific details about what you need assistance with? For example:\n- Product questions or technical support\n- Refund or return requests\n- Account or order inquiries",
                "confidence": parsed_result.get("confidence", "medium"),
                "needs_routing": False,
                "resolved": False,
                "needs_clarification": True
            }