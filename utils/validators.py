import re
from typing import Dict, List, Tuple, Optional

class InputValidator:
    """Input Validator: handles input validation for the customer support.
    We use static method and regex to ensure the user input is valid as expected in the database.

    At the end, we also include the validator for the API key.
    """
    
    @staticmethod
    def validate_invoice_number(invoice_no: str) -> Tuple[bool, str]:
        """Validate invoice number format"""
        if not invoice_no:
            return False, "Invoice number is required."
        
        # Expected format: INV followed by 4 digits
        pattern = r'^INV\d{4}$'
        if not re.match(pattern, invoice_no):
            return False, "Invoice number must be in format INV#### (e.g., INV1001)."
        
        return True, ""
    
    @staticmethod
    def validate_customer_id(customer_id: str) -> Tuple[bool, str]:
        """Validate customer ID format"""
        if not customer_id:
            return False, "Customer ID is required."
        
        # Expected format: CUST followed by 3 digits
        pattern = r'^CUST\d{3}$'
        if not re.match(pattern, customer_id):
            return False, "Customer ID must be in format CUST### (e.g., CUST123)."
        
        return True, ""
    
    @staticmethod
    def validate_refund_reason(reason: str) -> Tuple[bool, str]:
        """Validate refund reason"""
        if not reason or len(reason.strip()) < 10:
            return False, "Please provide a detailed reason (at least 10 characters)."
        
        if len(reason) > 500:
            return False, "Reason is too long (maximum 500 characters)."
        
        return True, ""
    
    @staticmethod
    def validate_query_input(query: str) -> Tuple[bool, str]:
        """Validate user query input"""
        if not query or len(query.strip()) < 3:
            return False, "Please provide a more detailed question (at least 3 characters)."
        
        if len(query) > 1000:
            return False, "Query is too long (maximum 1000 characters)."
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Simple sanitize function for user input"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        sanitized = ' '.join(text.strip().split())
        
        # Remove potentially harmful characters
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        return sanitized
    
    @staticmethod
    def extract_transaction_info(text: str) -> Dict[str, Optional[str]]:
        """Extract transaction information from user input"""
        text_upper = text.upper()
        
        # Extract invoice number
        invoice_match = re.search(r'INV\d{4}', text_upper)
        invoice_no = invoice_match.group() if invoice_match else None
        
        # Extract customer ID
        customer_match = re.search(r'CUST\d{3}', text_upper)
        customer_id = customer_match.group() if customer_match else None
        
        return {
            "invoice_no": invoice_no,
            "customer_id": customer_id
        }
    
    @staticmethod
    def classify_query_intent(query: str) -> str:
        """Simple rule-based intent classification"""
        query_lower = query.lower()
        
        # Refund-related keywords
        refund_keywords = [
            "refund", "return", "money back", "cancel order", 
            "invoice", "inv", "receipt", "transaction"
        ]
        
        # FAQ-related keywords
        faq_keywords = [
            "product", "specification", "specs", "dimension", 
            "feature", "how to", "compatible", "warranty", 
            "shipping", "payment", "policy"
        ]
        
        # Partnership keywords
        partnership_keywords = [
            "partnership", "business", "wholesale", "bulk", 
            "distributor", "reseller", "collaborate"
        ]
        
        # Count keyword matches
        refund_score = sum(1 for keyword in refund_keywords if keyword in query_lower)
        faq_score = sum(1 for keyword in faq_keywords if keyword in query_lower)
        partnership_score = sum(1 for keyword in partnership_keywords if keyword in query_lower)
        
        # Determine intent based on highest score
        if refund_score > faq_score and refund_score > partnership_score:
            return "refund"
        elif partnership_score > faq_score and partnership_score > refund_score:
            return "partnership"
        elif faq_score > 0:
            return "faq"
        else:
            return "other"
    
    @staticmethod
    def is_complete_refund_request(query: str) -> bool:
        """Check if refund request contains necessary information"""
        extracted = InputValidator.extract_transaction_info(query)
        return bool(extracted["invoice_no"] and extracted["customer_id"])
    
    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, str]:
        """Validate OpenAI API key format"""
        if not api_key:
            return False, "API key is required."
        
        if not api_key.startswith('sk-'):
            return False, "Invalid API key format. Should start with 'sk-'."
        
        if len(api_key) < 20:
            return False, "API key seems too short."
        
        return True, ""