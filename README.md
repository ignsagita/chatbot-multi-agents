# Customer Support AI System

This project showcases a multi-agent customer support system built with Python, OpenAI, and Streamlit. It uses intelligent routing to handle refunds, product FAQs, and general inquiries, simulating how a chatbot manages customer interactions in e-commerce.

## Live Demo
[View Demo](https://crm-chatbot-multi-agents.streamlit.app/) |
[View YouTube video](https://www.youtube.com/watch?v=whBXf9XVxlw)

## Features

### Multi-Agent Architecture
- **Triage (classifier) Agent**: Intelligently classifies and routes customer queries (query classification, intent detection, routing decisions)
- **Refund (specialized) Agent**: Handles return requests with transaction verification (transaction verification, refund processing, customer validation)
- **FAQ (specialized) Agent**: Answers product and policy questions using knowledge base (knowledge base search, answer synthesis, confidence scoring)

**Why Multi-Agent Architecture?**
- Separation of Concerns: Each agent specializes in specific domains
- Scalability: Easy to add new agent types or modify existing ones
- Maintainability: Clear boundaries between different business logic
- Testing: Independent testing of each agent's functionality

### Smart Query Processing
- Natural language understanding for intent classification
- Automatic extraction of transaction details (Invoice numbers, Customer IDs)
- Fuzzy matching for FAQ searches with confidence scoring

### Session Management
- SQLite database for conversation logging
- Session-based context preservation, query limits, and timeout handling
- Automated cleanup for privacy compliance
- Export capabilities for CRM integration

### Caching Strategy
- *Response Caching*: Reduces API costs for repeated queries
- Session Context: Maintains conversation state
- TTL Management: Prevents stale data issues

### Analytics & Reporting
- Downloadable chat logs and refund requests
- Real-time session statistics
- CRM team integration ready

### Input Validation & Security
- Sufficient input sanitization
- Transaction verification against database
- Error handling with proper fallbacks


##  Quick Setup

### Prerequisites
- Python 3.12+
- OpenAI API key
- Git

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-username/crm-multi-agents.git
cd crm-multi-agents
```

2. **Run the setup script**
```bash
python setup.py
```
This creates the directory structure, generates mock data, and creates `.env` template.

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API key**
Edit `.env` file:
```env
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo    # Cost-effective for demo
MAX_TOKENS=150                # Control API costs
TEMPERATURE=0.1              # Consistent responses

MAX_QUERIES_PER_SESSION=30    # Rate limiting
SESSION_TIMEOUT=1800          # 30 minutes
CACHE_TTL=300                # 5-minute response cache
```

5. **Generate mock data** (if not done by setup.py)
```bash
python create_mock_data.py
```

6. **Launch the application**
```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

### Docker Setup

```bash
# Clone and setup
git clone https://github.com/your-username/crm-multi-agents.git
cd crm-multi-agents

# Create .env with your API key
echo "OPENAI_API_KEY=your-key-here" > .env

# Build and run
docker build -t crm-support-ai .
docker run -p 8501:8501 --env-file .env crm-support-ai
```

## Usage

### Sample Interactions

**Refund Requests:**
```
User: "I want to return my wireless headphones from order INV1001, customer CUST267"
System: Verifies transaction → Processes refund → Logs request
```

**Product FAQ:**
```
User: "What are the dimensions of PRD001?"
System: Searches knowledge base → Returns specifications → Logs interaction
```

**General Inquiries:**
```
User: "How can I track my order?"
System: Provides tracking information → Offers additional help
```

## Project Structure

```
crm-multi-agents/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py       # Abstract base class for all agents
│   ├── triage_agent.py     # Query classification and routing
│   ├── refund_agent.py     # Refund request processing
│   └── faq_agent.py        # FAQ and product information
├── utils/
│   ├── __init__.py
│   ├── database.py         # SQLite session management
│   ├── validators.py       # Input validation and sanitization
│   └── response_schema.py  # Standardized response format
├── data/
│   ├── transactions.csv    # Mock transaction database
│   ├── faq.json           # Knowledge base
│   └── session_logs.db    # SQLite session storage
├── config.py              # Configuration management
├── app.py                 # Main Streamlit application
├── create_mock_data.py    # Data generation script
├── setup.py               # Project initialization
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
└── .env                   # Environment variables (create from template)
```

## Database Structure
Generated by create_mock_data.py execution.

### Transaction Database Schema
```csv
InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID
INV1001,PRD008,Gaming Keyboard,3,2025-07-17,89.99,CUST267
```

### FAQ Knowledge Base Structure
```json
{
  "records": [
    {
      "id": 1,
      "category": "return_policy",
      "question": "What is the return policy?",
      "answer": "Items can be returned within 30 days...",
      "keywords": ["return", "policy", "refund", "30 days"]
    }
  ]
}
```

## Future Enhancements
- [ ] **Live Chat Integration**: Real-time customer support
- [ ] **API Endpoints**: RESTful API for external integrations
- [ ] **Admin Dashboard**: CRM team management interface
- [ ] **Advanced Analytics**: ML-powered conversation and traffic insights

## Contributing

1. Fork or star the repository
2. Create a feature branch: `git checkout -b feature/your-feature` and make your changes
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request


## Acknowledgments

- OpenAI for providing the GPT models
- Streamlit for the web framework
- The open-source community for inspiration and tools

---
