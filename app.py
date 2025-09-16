import streamlit as st
import pandas as pd
import json
import sqlite3
from datetime import datetime
import io
import os
import sys
from io import StringIO

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
model = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
max_tokens = st.secrets.get("MAX_TOKENS", int(os.getenv("MAX_TOKENS", 150)))
temperature = st.secrets.get("TEMPERATURE", float(os.getenv("TEMPERATURE", 0.1)))

# Import your modules
try:
    from agents.triage_agent import TriageAgent
    from agents.refund_agent import RefundAgent
    from agents.faq_agent import FAQAgent
    from utils.database import DatabaseManager, generate_session_id, is_session_valid
    from config import Config
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error("Please make sure files are in the correct directory structure:")
    st.error("- agents/triage_agent.py")
    st.error("- agents/refund_agent.py") 
    st.error("- agents/faq_agent.py")
    st.error("- utils/database.py")
    st.error("- config.py")
    st.stop()

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Customer Support AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        margin-left: 2rem;
        text-align: right;
    }
    
    .agent-message {
        background-color: #e9ecef;
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        margin-right: 2rem;
    }
    
    .sidebar-info {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class CustomerSupportApp:
    """Main Streamlit apps for Customer Support AI"""
    
    def __init__(self):
        try:
            self.db = DatabaseManager()
            self.initialize_session_state()
            self.initialize_agents()
        except Exception as e:
            st.error(f"Error initializing app: {e}")
            logger.error(f"App initialization error: {e}")
            raise
    
    def initialize_session_state(self):
        """Initialize Streamlit session state"""
        if "session_id" not in st.session_state:
            st.session_state.session_id = generate_session_id()
            self.db.create_session(st.session_state.session_id)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "customer_info" not in st.session_state:
            st.session_state.customer_info = {}
        
        if "current_context" not in st.session_state:
            st.session_state.current_context = {}
        
        if "awaiting_info" not in st.session_state:
            st.session_state.awaiting_info = False
        
        if "required_fields" not in st.session_state:
            st.session_state.required_fields = []

        self._load_context_from_db() 
    
    def _save_context_to_db(self):
        """Save session context to database"""
        try:
            context_data = {
                'customer_info': st.session_state.customer_info,
                'current_context': st.session_state.current_context,
                'awaiting_info': st.session_state.awaiting_info,
                'required_fields': st.session_state.required_fields
            }
            
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO session_context 
                    (session_id, context_data, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)""",
                    (st.session_state.session_id, json.dumps(context_data))
                )
        except Exception as e:
            logger.error(f"Error saving context: {e}")

    def _load_context_from_db(self):
        """Load session context from database"""
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                cursor = conn.execute(
                    "SELECT context_data FROM session_context WHERE session_id = ?",
                    (st.session_state.session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    context_data = json.loads(row[0])
                    st.session_state.customer_info = context_data.get('customer_info', {})
                    st.session_state.current_context = context_data.get('current_context', {})
                    st.session_state.awaiting_info = context_data.get('awaiting_info', False)
                    st.session_state.required_fields = context_data.get('required_fields', [])
                    
        except Exception as e:
            logger.error(f"Error loading context: {e}")

    def initialize_agents(self):
        """Initialize AI agents"""
        try:
            # Get API key from config or environment
            api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
            
            if not api_key:
                st.error("⚠️ OpenAI API key not configured. Please set OPENAI_API_KEY in Streamlit secret or .env file.")
                st.stop()
            
            self.triage_agent = TriageAgent(api_key)
            self.refund_agent = RefundAgent(api_key)
            self.faq_agent = FAQAgent(api_key)

            logger.info("Agents initialized successfully")
            
        except Exception as e:
            st.error(f"Error initializing agents: {e}")
            logger.error(f"Agent initialization error: {e}")
            st.stop()
    
    def render_sidebar(self):
        """Render sidebar with session info and controls"""
        with st.sidebar:
                        
            # Customer information form
            st.markdown("## For a better service of our CRM team, leave your contact information here:")
            
            with st.form("customer_info_form"):
                customer_id = st.text_input(
                    "Customer ID", 
                    value=st.session_state.customer_info.get('customer_id', ''),
                    help="Enter your customer ID (e.g., CUST123)"
                )
                
                email = st.text_input(
                    "Email", 
                    value=st.session_state.customer_info.get('email', ''),
                    help="Your registered email address"
                )
                
                phone = st.text_input(
                    "Phone", 
                    value=st.session_state.customer_info.get('phone', ''),
                    help="Your phone number"
                )
                
                submitted = st.form_submit_button("Update Information")
                
                if submitted:
                    st.session_state.customer_info = {
                        'customer_id': customer_id,
                        'email': email,
                        'phone': phone
                    }
                    st.success("✅ Customer information updated!")
            
            st.markdown("---")
            st.markdown("*UNSEEN FOR CUSTOMERS*")
            st.markdown("## 📊 Session Information")
            
            # Session info
            session_info = self.db.get_session_info(st.session_state.session_id)
            if session_info:
                st.markdown(f"""
                <div class="sidebar-info">
                    <strong>Session ID:</strong> {st.session_state.session_id[:8]}...<br>
                    <strong>Queries:</strong> {session_info['query_count']}<br>
                    <strong>Started:</strong> {session_info['created_at'][:19]}
                </div>
                """, unsafe_allow_html=True)

            # Download buttons
            st.markdown("## 📥 Download Reports")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📋 Chat Logs", use_container_width=True):
                    self.download_chat_logs()
            
            with col2:
                if st.button("💰 Refunds", use_container_width=True):
                    self.download_refund_requests()
            
            # Clear session
            st.markdown("## 🔄 Session Controls")
            if st.button("🗑️ Clear Session", use_container_width=True):
                self.clear_session()
    
    def render_main_chat(self):
        """Render main chat interface"""
        st.markdown('<div class="main-header">🤖 Customer Support AI Assistant</div>', unsafe_allow_html=True)
        
        with st.expander("README"):
            st.markdown("""
            This project showcases a multi-agent customer support system built with Python, 
            OpenAI, and Streamlit. It uses intelligent routing to handle refunds, product FAQs, 
            and general inquiries, simulating how a chatbot manages customer interactions in e-commerce.”
                        
            See full repository on: [Github](github.com/ignsagita/crm-multi-agents)
            """)

        with st.expander("🔄 Refund Requests sample prompts"):
            st.markdown("""
            - "I want to return my wireless headphones"  
            - "Need a refund for order INV1001"  
            _System will verify transaction details before processing_
            """)

        with st.expander("❓ Product FAQ sample prompts"):
            st.markdown("""
            - "What are the dimensions of PRD001?"  
            - "What's your return policy?"  
            - "Do you ship internationally?"  
            """)

        with st.expander("🤝 General Inquiries sample prompts"):
            st.markdown("""
            - "How can I track my order?"  
            - "I need help with my account"
            """)

        data = """InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID
        INV1000,PRD001,Wireless Bluetooth Headphones,3,2025-09-04,79.99,CUST602
        INV1001,PRD008,Gaming Keyboard,3,2025-07-17,89.99,CUST267
        INV1002,PRD003,USB-C Cable,3,2025-06-27,12.99,CUST326
        INV1003,PRD006,Power Bank,2,2025-09-07,39.99,CUST415
        INV1004,PRD004,Laptop Stand,2,2025-07-26,45.99,CUST711
        INV1005,PRD009,Webcam HD,2,2025-07-24,59.99,CUST167
        INV1006,PRD008,Gaming Keyboard,2,2025-06-28,89.99,CUST655
        INV1008,PRD005,Wireless Mouse,2,2025-09-13,29.99,CUST816
        INV1010,PRD007,Screen Protector,2,2025-07-03,9.99,CUST540
        INV1012,PRD002,Smartphone Case,3,2025-08-09,24.99,CUST624
        INV1016,PRD010,Bluetooth Speaker,2,2025-06-29,49.99,CUST280
        INV1017,PRD009,Webcam HD,2,2025-09-14,59.99,CUST808
        """

        # Convert the CSV string into a DataFrame
        df = pd.read_csv(StringIO(data))

        # Show the table (interactive)
        st.write("Transaction data in backend:")
        st.dataframe(df)

        # Welcome message
        if not st.session_state.messages:
            welcome_msg = """
            👋 **Welcome to Customer Support!**
            
            I'm here to help you with:
            - 💰 **Refund requests** - Process returns and refunds
            - ❓ **Product FAQ** - Answer questions about products and policies
            - 🤝 **General inquiries** - Other support needs
            
            Please describe how I can assist you today!
            """
            
            with st.chat_message("assistant"):
                st.markdown(welcome_msg)
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show additional info if available
                if "metadata" in message:
                    metadata = message["metadata"]
                    if metadata.get("category"):
                        st.caption(f"Category: {metadata['category']}")
                    if not metadata.get("resolved", True):
                        st.warning("Waiting for user's answer.....")
        
        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            self.process_user_message(prompt)
    
    def process_user_message(self, user_input: str):
        """Process user message through the agent system"""

        # Check session validity
        if not is_session_valid(self.db, st.session_state.session_id):
            st.error("⌛ Session limit reached. Please start a new session.")
            return
        
        logger.info(f"Processing user input: {user_input}")
        
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Update session activity
        self.db.update_session_activity(st.session_state.session_id)
        
        # Process with agents
        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                response = self.route_and_process(user_input)
            
            st.markdown(response["content"])
            
            # Show metadata if available
            if "metadata" in response:
                metadata = response["metadata"]
                if metadata.get("category"):
                    st.caption(f"Category: {metadata['category']}")
                if not metadata.get("resolved", True):
                    st.warning("Waiting for user's answer ...")
        
        # Add assistant response to chat
        st.session_state.messages.append(response)
        
        # Log conversation
        self.db.log_conversation(
            st.session_state.session_id,
            user_input,
            response["content"],
            response.get("metadata", {}).get("category", "general"),
            response.get("metadata", {}).get("resolved", True),
            response.get("metadata", {}).get("needs_followup", False)
        )

        self._load_context_from_db() 
    
    def _determine_routing(self, triage_result: dict, user_input: str, context: dict) -> dict:
        """Enhanced routing logic with tie-breaking"""
        category = triage_result.get("category", "other")
        confidence = triage_result.get("confidence", 0.5)
        
        # Convert string confidence to numeric
        if isinstance(confidence, str):
            confidence_map = {"high": 0.8, "medium": 0.6, "low": 0.4}
            confidence = confidence_map.get(confidence, 0.5)
        
        # Intent strength analysis
        refund_indicators = ["refund", "return", "money back", "inv", "invoice"]
        faq_indicators = ["how", "what", "policy", "specification", "dimension"]
        
        refund_strength = sum(1 for word in refund_indicators if word in user_input.lower())
        faq_strength = sum(1 for word in faq_indicators if word in user_input.lower())
        
        # Enhanced routing decision
        if category == "refund" and confidence > 0.6:
            return {"route_to": "refund", "confidence": confidence}
        elif category == "faq" and confidence > 0.6:
            return {"route_to": "faq", "confidence": confidence}
        elif refund_strength > faq_strength and refund_strength > 0:
            return {"route_to": "refund", "confidence": 0.7}
        elif faq_strength > refund_strength and faq_strength > 0:
            return {"route_to": "faq", "confidence": 0.7}
        else:
            return {"route_to": "triage", "confidence": confidence}


    def route_and_process(self, user_input: str) -> dict:
        """Route user input to appropriate agent and process response"""
        try:
            logger.info("Starting routing process")
            
            # Prepare context
            context = {
                "session_id": st.session_state.session_id,
                "customer_info": st.session_state.customer_info,
                "previous_context": st.session_state.current_context
            }
            
            # First, use triage agent to determine category
            logger.info("Calling triage agent")
            triage_result = self.triage_agent.process(user_input, context)
            if hasattr(triage_result, 'to_dict'):
                triage_result = triage_result.to_dict()
            logger.info(f"Triage result: {triage_result}")

            category = triage_result.get("category", "general")
            confidence = triage_result.get("confidence", 0.5)

            # Convert string confidence to numeric if needed
            if isinstance(confidence, str):
                confidence_map = {"high": 0.8, "medium": 0.6, "low": 0.4}
                confidence = confidence_map.get(confidence, 0.5)

            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            
            logger.info(f"Category: {category}, Confidence: {confidence}")
            
            # Route to appropriate specialist agent

            # Enhanced routing with tie-breaking logic
            route_decision = self._determine_routing(triage_result, user_input, context)
            if route_decision["route_to"] == "refund":
                logger.info("Routing to refund agent")
                result = self.refund_agent.process(user_input, context)
                
                # Handle refund-specific logic
                if result.get("requires_verification"):
                    st.session_state.awaiting_info = True
                    st.session_state.required_fields = result.get("required_fields", [])
                
                # Log refund request if completed
                if result.get("refund_data"):
                    self.db.log_refund_request(
                        st.session_state.session_id,
                        result["refund_data"]
                    )
                
            elif route_decision["route_to"] == "faq":
                logger.info("Routing to FAQ agent")
                result = self.faq_agent.process(user_input, context)
                
            else:
                logger.info("Using triage agent response")
                # Use triage agent for general responses
                result = triage_result
            
            logger.info(f"Final result: {result}")

            # Update current context
            st.session_state.current_context = result.get("context", {})
            
            return {
                "role": "assistant",
                "content": result.get("response", "I apologize, but I couldn't process your request."),
                "metadata": {
                    "category": category,
                    "confidence": confidence,
                    "resolved": result.get("resolved", True),
                    "needs_followup": result.get("needs_followup", False)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "role": "assistant",
                "content": "I apologize, but I encountered an error processing your request. Please try again or contact our support team.",
                "metadata": {
                    "category": "error",
                    "resolved": False,
                    "needs_followup": True
                }
            }
    
    def download_chat_logs(self):
        """Generate and download chat logs CSV"""
        try:
            df = self.db.get_session_logs_csv(st.session_state.session_id)
            
            if df.empty:
                st.warning("No chat logs found for this session.")
                return
            
            # Convert DataFrame to CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Create download button
            st.download_button(
                label="📋 Download Chat Logs",
                data=csv_data,
                file_name=f"chat_logs_{st.session_state.session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Chat logs ready for download ({len(df)} records)")
            
        except Exception as e:
            st.error(f"Error generating chat logs: {e}")
    
    def download_refund_requests(self):
        """Generate and download refund requests CSV"""
        try:
            df = self.db.get_refund_requests_csv(st.session_state.session_id)
            
            if df.empty:
                st.warning("No refund requests found for this session.")
                return
            
            # Convert DataFrame to CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Create download button
            st.download_button(
                label="💰 Download Refund Requests",
                data=csv_data,
                file_name=f"refund_requests_{st.session_state.session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Refund requests ready for download ({len(df)} records)")
            
        except Exception as e:
            st.error(f"Error generating refund requests: {e}")
    
    def clear_session(self):
        """Clear current session and start fresh"""
        try:
            # Clean up database
            self.db.cleanup_session_data(st.session_state.session_id)
            
            # Reset session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.success("✅ Session cleared successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error clearing session: {e}")
    
    def run(self):
        """Main application entry point"""
        # Check if data files exist
        self.check_data_files()
        
        # Render UI components
        self.render_sidebar()
        self.render_main_chat()
        
        # Show system status in footer
        self.render_footer()
    
    def check_data_files(self):
        """Check if required data files exist"""
        missing_files = []
        
        if not os.path.exists("data/transactions.csv"):
            missing_files.append("transactions.csv")
        
        if not os.path.exists("data/faq.json"):
            missing_files.append("faq.json")
        
        if missing_files:
            st.error(f"""
            ❌ **Missing Data Files:** {', '.join(missing_files)}
            
            Please run the data generation script first:
            ```python
            python generate_mock_data.py
            ```
            """)
            st.stop()
    
    def render_footer(self):
        """Render footer with system information"""
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Transaction data status
            try:
                df = self.db.get_transactions_data()
                st.markdown(f"📊 **Transactions:** {len(df)} records")
            except:
                st.markdown("📊 **Transactions:** ❌ Error")
        
        with col2:
            # FAQ data status
            try:
                faq_data = self.db.get_faq_data()
                st.markdown(f"❓ **FAQ Entries:** {len(faq_data.get('records', []))} records")
            except:
                st.markdown("❓ **FAQ Entries:** ❌ Error")
        
        with col3:
            # Session status
            session_info = self.db.get_session_info(st.session_state.session_id)
            if session_info:
                remaining = Config.MAX_QUERIES_PER_SESSION - session_info['query_count']
                if remaining > 10:
                    status_class = "status-success"
                elif remaining > 5:
                    status_class = "status-warning"
                else:
                    status_class = "status-error"
                
                st.markdown(f'<span class="{status_class}">🔄 **Queries Remaining:** {remaining}</span>', unsafe_allow_html=True)


def main():
    """Main function to run the Streamlit app"""
    try:
        app = CustomerSupportApp()
        app.run()
    except Exception as e:
        st.error(f"Application error: {e}")
        logger.error(f"Application error: {e}")


if __name__ == "__main__":
    main()
