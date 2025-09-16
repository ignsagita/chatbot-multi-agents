from .base_agent import BaseAgent
from utils.validators import InputValidator
from utils.database import DatabaseManager
from utils.response_schema import AgentResponse
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RefundAgent(BaseAgent):
    """Specialized agent for handling refund requests"""
    
    def __init__(self, api_key: str):
        super().__init__("RefundAgent", api_key)
        self.validator = InputValidator()
        self.db = DatabaseManager()
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for refund processing."""
        return """You are a customer service specialist handling refund requests. Follow these steps:

1. VERIFICATION: Confirm transaction details match our records
2. REASON: Ask for and document the refund reason
3. POLICY: Apply our 30-day return policy
4. PROCESS: Guide customer through next steps

REFUND POLICY:
- Items can be returned within 30 days of purchase
- Original receipt/invoice required
- Refunds processed to original payment method
- Processing time: 5-7 business days

TONE: Professional, empathetic, and solution-oriented

When transaction is verified:
- Acknowledge the verified purchase
- Ask for refund reason if not provided
- Explain next steps clearly
- Provide timeline expectations

When transaction cannot be verified:
- Politely explain the issue
- Ask customer to double-check details
- Offer alternative solutions if appropriate

Always be helpful and understanding while following company policy."""
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process refund request with transaction verification"""
        try:
            context = context or {}
            
            # Extract transaction info from input
            extracted_info = self.validator.extract_transaction_info(user_input)
            invoice_no = extracted_info.get("invoice_no")
            customer_id = extracted_info.get("customer_id")
            
            # Check if we have transaction info from previous context
            if not invoice_no and context.get("extracted_info"):
                invoice_no = context["extracted_info"].get("invoice_no")
                customer_id = context["extracted_info"].get("customer_id")
            
            # If we still don't have complete info, ask for it
            if not invoice_no or not customer_id:
                return self._request_transaction_info(extracted_info)
            
            # Verify transaction in database
            transaction = self.db.verify_transaction(invoice_no, customer_id)
            
            if not transaction:
                return self._handle_transaction_not_found(invoice_no, customer_id)
            
            # Transaction verified - process refund
            return self._process_verified_refund(user_input, transaction, context)
            
        except Exception as e:
            logger.error(f"Error in refund processing: {e}")
            return AgentResponse(
                response="I apologize, but I'm experiencing technical difficulties. Please contact our customer service team directly for refund assistance.",
                resolved=False,
                category="refund",
                needs_followup=True
            ).to_dict()
    
    def _request_transaction_info(self, extracted_info: Dict) -> Dict[str, Any]:
        """Request missing transaction information"""
        missing_fields = []
        if not extracted_info.get("invoice_no"):
            missing_fields.append("Invoice Number (format: INV####)")
        if not extracted_info.get("customer_id"):
            missing_fields.append("Customer ID (format: CUST###)")
        
        response = f"To process your refund request, I need the following information:\n"
        response += "\n".join(f"• {field}" for field in missing_fields)
        response += " and please tell us the reason of return.\n\nYou can find these details in your order confirmation email or receipt."
        
        return AgentResponse(
            response=response,
            resolved=False,
            category="refund",
            needs_more_info=True,
            metadata={"missing_fields": missing_fields}
        ).to_dict()
    
    def _handle_transaction_not_found(self, invoice_no: str, customer_id: str) -> Dict[str, Any]:
        """Handle case where transaction is not found."""
        response = f"""I couldn't find a transaction matching:
• Invoice Number: {invoice_no}
• Customer ID: {customer_id}

Please double-check these details. Common issues:
• Make sure the invoice number includes 'INV' (e.g., INV1001)
• Verify the customer ID format (e.g., CUST123)
• Check if you're using details from the correct order

If you're certain the details are correct, please contact our customer service team for further assistance."""
        
        return AgentResponse(
            response=response,
            resolved=False,
            category="refund",
            needs_followup=True,
            metadata={"transaction_found": False}
        ).to_dict()
    
    def _process_verified_refund(self, user_input: str, transaction: Dict, context: Dict) -> Dict[str, Any]:
        """Process refund for verified transaction"""
        # Check if we already have a refund reason
        refund_reason = self._extract_refund_reason(user_input)
        
        if not refund_reason and not context.get("refund_reason"):
            return self._request_refund_reason(transaction)
        
        # Use existing reason from context if available
        if not refund_reason:
            refund_reason = context.get("refund_reason")
        
        # Validate refund reason
        is_valid_reason, reason_error = self.validator.validate_refund_reason(refund_reason)
        if not is_valid_reason:
            return AgentResponse(
                response=f"Please provide a more detailed refund reason. {reason_error}",
                resolved=False,
                category="refund",
                needs_more_info=True
            ).to_dict()
        
        # Generate AI response for the refund
        if self.client:
            ai_prompt = f"""Customer Details:
Invoice: {transaction['InvoiceNo']}
Product: {transaction['Description']} (SKU: {transaction['StockCode']})
Quantity: {transaction['Quantity']}
Price: ${transaction['UnitPrice']}
Date: {transaction['InvoiceDate']}
Customer: {transaction['CustomerID']}

Refund Reason: {refund_reason}

Provide a professional response acknowledging the refund request and explaining next steps."""
            
            ai_response = self.process_with_cache(
                f"Refund request for {transaction['Description']}. Reason: {refund_reason}",
                self.get_system_prompt() + f"\n\nTransaction Details: {str(transaction)}"
            )
        else:
            ai_response = self._generate_standard_refund_response(transaction, refund_reason)
        
        # Prepare refund data for logging
        refund_data = {
            "customer_id": transaction['CustomerID'],
            "invoice_no": transaction['InvoiceNo'],
            "stock_code": transaction['StockCode'],
            "product_description": transaction['Description'],
            "quantity": transaction['Quantity'],
            "unit_price": transaction['UnitPrice'],
            "refund_reason": refund_reason
        }
        
        return AgentResponse(
            response=ai_response,
            resolved=True,
            category="refund",
            confidence=0.9,
            metadata={
                "refund_data": refund_data,
                "transaction_verified": True
            }
        ).to_dict()
    
    def _extract_refund_reason(self, user_input: str) -> Optional[str]:
        """Extract refund reason from user input"""
        # Simple extraction - look for common reason patterns
        reason_indicators = [
            "because", "reason", "due to", "since", "as", "defective", 
            "broken", "not working", "wrong", "mistake", "changed mind"
        ]
        
        input_lower = user_input.lower()
        for indicator in reason_indicators:
            if indicator in input_lower:
                # Try to extract the part after the indicator
                parts = input_lower.split(indicator, 1)
                if len(parts) > 1:
                    potential_reason = parts[1].strip()
                    if len(potential_reason) > 10:  # Minimum reason length
                        return potential_reason[:500]  # Max reason length
        
        # If no specific reason found but input is substantial, use whole input
        if len(user_input.strip()) > 20:
            return user_input.strip()[:500]
        
        return None
    
    def _request_refund_reason(self, transaction: Dict) -> Dict[str, Any]:
        """Request refund reason from customer"""
        response = f"""Great! I found your transaction:

 **Product**: {transaction['Description']}
 **SKU ID**: {transaction['StockCode']}
 **Purchase Date**: {transaction['InvoiceDate']}
 **Amount**: ${transaction['UnitPrice']} x {transaction['Quantity']}

To complete your refund request, please tell me the reason for the return. For example:
• Product defective or damaged
• Wrong item received
• Changed mind about purchase
• Product doesn't meet expectations
• Other reason (please specify)"""
        
        return AgentResponse(
            response=response,
            resolved=False,
            category="refund",
            needs_more_info=True,
            metadata={
                "transaction_verified": True,
                "awaiting_reason": True
            }
        ).to_dict()
    
    def _generate_standard_refund_response(self, transaction: Dict, reason: str) -> str:
        """Generate standard refund response when AI is not available"""
        return f"""Thank you for providing the refund details. I've processed your refund request:

 **Product**: {transaction['Description']}
 **Invoice**: {transaction['InvoiceNo']}
 **Reason**: {reason}
 **Refund Amount**: ${float(transaction['UnitPrice']) * int(transaction['Quantity']):.2f}

**Next Steps**:
1. Your refund request has been submitted to our processing team
2. You'll receive a confirmation email within 2 business hours
3. Refund will be processed to your original payment method
4. Expected processing time: 5-7 business days

**Return Instructions** (if applicable):
- Package the item securely in original packaging
- Use the return label that will be emailed to you
- Drop off at any authorized shipping location

Is there anything else I can help you with regarding this refund?"""