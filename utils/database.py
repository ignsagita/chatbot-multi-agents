import sqlite3
import pandas as pd
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import Config
import os
import difflib

class DatabaseManager:
    """DatabaseManager: handles all database operations for the customer support system, including:
    - Session management using SQLite
    - Log conversation exchanges
    - Log refund requests
    - Load transaction data
    - Load FAQ data
    - Load FAQ data
    - Verify if transaction exists in the system
    - Simple keyword-based FAQ search
    - Get session logs as DataFrame for CSV export
    - Get refund requests as DataFrame for CSV export
    - Clean up session data for privacy

    Additional utility function:
    - Generate a unique session ID
    - Check if session is valid and within limits
    """
    
    def __init__(self):
        self.ensure_directories()
        self.init_session_db()
        
    def ensure_directories(self):
        """Check if data directory exists"""
        os.makedirs("data", exist_ok=True)
    
    def init_session_db(self):
        """Initialize database for session management"""
        with sqlite3.connect(Config.DB_PATH) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query_count INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT,
                    agent_response TEXT,
                    category TEXT,
                    resolved BOOLEAN DEFAULT TRUE,
                    needs_followup BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                
                CREATE TABLE IF NOT EXISTS refund_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    customer_id TEXT,
                    invoice_no TEXT,
                    stock_code TEXT,
                    product_description TEXT,
                    quantity INTEGER,
                    unit_price REAL,
                    refund_reason TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                               
                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    context_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
            """)
    
    def create_session(self, session_id: str) -> bool:
        """Create a session"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO sessions (session_id) VALUES (?)",
                    (session_id,)
                )
                return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session's last activity"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.execute(
                    """UPDATE sessions 
                       SET last_activity = CURRENT_TIMESTAMP,
                           query_count = query_count + 1
                       WHERE session_id = ?""",
                    (session_id,)
                )
                return True
        except Exception as e:
            print(f"Error updating session: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "session_id": row[0],
                        "created_at": row[1],
                        "last_activity": row[2],
                        "query_count": row[3]
                    }
                return None
        except Exception as e:
            print(f"Error getting session info: {e}")
            return None
    
    def log_conversation(self, session_id: str, user_input: str, 
                        agent_response: str, category: str, 
                        resolved: bool = True, needs_followup: bool = False):
        """Log a conversation exchange"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.execute(
                    """INSERT INTO conversation_logs 
                       (session_id, user_input, agent_response, category, resolved, needs_followup)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (session_id, user_input, agent_response, category, resolved, needs_followup)
                )
        except Exception as e:
            print(f"Error logging conversation: {e}")
    
    def log_refund_request(self, session_id: str, refund_data: Dict):
        """Log a refund request"""
        conn = None
        try:
            conn = sqlite3.connect(Config.DB_PATH)
            conn.execute("BEGIN")
            
            conn.execute(
                """INSERT INTO refund_requests 
                (session_id, customer_id, invoice_no, stock_code, 
                    product_description, quantity, unit_price, refund_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    refund_data.get("customer_id"),
                    refund_data.get("invoice_no"),
                    refund_data.get("stock_code"),
                    refund_data.get("product_description"),
                    refund_data.get("quantity"),
                    refund_data.get("unit_price"),
                    refund_data.get("refund_reason")
                )
            )
            
            # Update session activity as part of transaction
            conn.execute(
                """UPDATE sessions 
                SET last_activity = CURRENT_TIMESTAMP,
                    query_count = query_count + 1
                WHERE session_id = ?""",
                (session_id,)
            )
            
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error logging refund request: {e}")
            raise
        
        finally:
            if conn:
                conn.close()
    
    def get_transactions_data(self) -> pd.DataFrame:
        """Load transaction data"""
        try:
            return pd.read_csv(Config.TRANSACTIONS_PATH)
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return pd.DataFrame()
    
    def get_faq_data(self) -> Dict:
        """Load FAQ data"""
        try:
            with open(Config.FAQ_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading FAQ: {e}")
            return {"records": []}
    
    def verify_transaction(self, invoice_no: str, customer_id: str) -> Optional[Dict]:
        """Verify if transaction exists in the system"""
        df = self.get_transactions_data()
        if df.empty:
            return None
        
        match = df[
            (df['InvoiceNo'] == invoice_no) & 
            (df['CustomerID'] == customer_id)
        ]
        
        if not match.empty:
            return match.iloc[0].to_dict()
        return None
    
    def search_faq(self, query: str, top_k: int = 3) -> List[Dict]:
        """Enhanced FAQ search with fuzzy matching"""
        faq_data = self.get_faq_data()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        scored_items = []
        for record in faq_data.get("records", []):
            score = 0
            
            # Exact keyword matches (highest priority)
            for keyword in record.get("keywords", []):
                if keyword.lower() in query_lower:
                    score += 3
            
            # Fuzzy matching on keywords
            for keyword in record.get("keywords", []):
                for query_word in query_words:
                    similarity = difflib.SequenceMatcher(None, keyword.lower(), query_word).ratio()
                    if similarity > 0.8:  # 80% similarity threshold
                        score += 2
                    elif similarity > 0.6:  # 60% similarity threshold
                        score += 1
            
            # Question/answer content matching
            question_words = record["question"].lower().split()
            answer_words = record["answer"].lower().split()
            
            for query_word in query_words:
                # Exact word matches
                if query_word in question_words:
                    score += 2
                if query_word in answer_words:
                    score += 1
                    
                # Fuzzy matches in question/answer
                for word in question_words:
                    if difflib.SequenceMatcher(None, word, query_word).ratio() > 0.8:
                        score += 1
            
            if score > 0:
                scored_items.append((score, record))
        
        # Sort by score and return top results
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_items[:top_k]]
    
    def get_session_logs_csv(self, session_id: str) -> pd.DataFrame:
        """Get session logs as DataFrame for CSV export"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                query = """
                    SELECT timestamp, user_input, agent_response, category, 
                           resolved, needs_followup 
                    FROM conversation_logs 
                    WHERE session_id = ? 
                    ORDER BY timestamp
                """
                return pd.read_sql_query(query, conn, params=(session_id,))
        except Exception as e:
            print(f"Error getting session logs: {e}")
            return pd.DataFrame()
    
    def get_refund_requests_csv(self, session_id: str) -> pd.DataFrame:
        """Get refund requests as DataFrame for CSV export"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                query = """
                    SELECT timestamp, customer_id, invoice_no, stock_code,
                           product_description, quantity, unit_price, 
                           refund_reason, status
                    FROM refund_requests 
                    WHERE session_id = ? 
                    ORDER BY timestamp
                """
                return pd.read_sql_query(query, conn, params=(session_id,))
        except Exception as e:
            print(f"Error getting refund requests: {e}")
            return pd.DataFrame()
    
    def cleanup_session_data(self, session_id: str):
        """Clean up session data for privacy"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.execute("DELETE FROM conversation_logs WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM refund_requests WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        except Exception as e:
            print(f"Error cleaning up session: {e}")

# Additional utility functions
def generate_session_id() -> str:
    """Generate a unique session ID"""
    timestamp = str(datetime.now().timestamp())
    return hashlib.md5(timestamp.encode()).hexdigest()[:12]

def is_session_valid(db: DatabaseManager, session_id: str) -> bool:
    """Check if session is valid and within limits"""
    session_info = db.get_session_info(session_id)
    if not session_info:
        return False
    
    return session_info["query_count"] < Config.MAX_QUERIES_PER_SESSION