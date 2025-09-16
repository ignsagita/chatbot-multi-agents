import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')  # Cost-effective for demo purposes
    MAX_TOKENS: int = int(os.getenv('MAX_TOKENS', '150'))  # Control costs
    TEMPERATURE: float = float(os.getenv('TEMPERATURE', '0.1'))  # To result consistent responses
    
    # App Configuration
    APP_TITLE = "AI Customer Support System"
    SESSION_TIMEOUT = 1800  # 30 minutes in seconds
    MAX_QUERIES_PER_SESSION = 30  # Limit API calls for demo purposes
    
    # Database Configuration
    DB_PATH = "data/session_logs.db"
    TRANSACTIONS_PATH = "data/transactions.csv"
    FAQ_PATH = "data/faq.json"
    
    # Cache Configuration
    CACHE_TTL = 300  # 5 minutes
    MAX_CACHE_SIZE = 100
    
    # Agent Categories
    CATEGORIES = {
        "refund": "Refund Request",
        "faq": "Product FAQ",
        "other": "Other"
    }

    # Streamlit
    STREAMLIT_THEME = {
        'primaryColor': '#1f77b4',
        'backgroundColor': '#ffffff',
        'secondaryBackgroundColor': '#f8f9fa',
        'textColor': '#333333'
    }
    
    
    # System Messages
    SYSTEM_MESSAGES = {
        "welcome": "Hej! Valkomen till denna AI Customer Support! Please select your inquiry type and provide details.",
        "not_found": "Naha! The information you provided was not found in our system. Please verify your details.",
        "human_followup": "Vi kommer! This query requires human assistance. Our CRM team will follow up with you soon.",
        "session_limit": "You've reached the maximum number of queries for this session. Please refresh to start again."
    }