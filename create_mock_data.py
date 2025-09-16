import pandas as pd
import json
import os
from datetime import datetime, timedelta
import random

def create_mock_transactions():
    """Create mock transaction data for the demo. In real apps, we can connect to the transaction data through API."""
    
    # Product data
    products = [
        {"StockCode": "PRD001", "Description": "Wireless Bluetooth Headphones", "UnitPrice": 79.99},
        {"StockCode": "PRD002", "Description": "Smartphone Case", "UnitPrice": 24.99},
        {"StockCode": "PRD003", "Description": "USB-C Cable", "UnitPrice": 12.99},
        {"StockCode": "PRD004", "Description": "Laptop Stand", "UnitPrice": 45.99},
        {"StockCode": "PRD005", "Description": "Wireless Mouse", "UnitPrice": 29.99},
        {"StockCode": "PRD006", "Description": "Power Bank", "UnitPrice": 39.99},
        {"StockCode": "PRD007", "Description": "Screen Protector", "UnitPrice": 9.99},
        {"StockCode": "PRD008", "Description": "Gaming Keyboard", "UnitPrice": 89.99},
        {"StockCode": "PRD009", "Description": "Webcam HD", "UnitPrice": 59.99},
        {"StockCode": "PRD010", "Description": "Bluetooth Speaker", "UnitPrice": 49.99}
    ]
    
    # Generate 20 transactions
    transactions = []
    base_date = datetime.now() - timedelta(days=90)
    
    for i in range(20):
        invoice_no = f"INV{1000 + i}"
        customer_id = f"CUST{random.randint(100, 999)}"
        product = random.choice(products)
        quantity = random.randint(1, 3)
        invoice_date = base_date + timedelta(days=random.randint(0, 90))
        
        transactions.append({
            "InvoiceNo": invoice_no,
            "StockCode": product["StockCode"],
            "Description": product["Description"],
            "Quantity": quantity,
            "InvoiceDate": invoice_date.strftime("%Y-%m-%d"),
            "UnitPrice": product["UnitPrice"],
            "CustomerID": customer_id
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(transactions)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Save to CSV
    df.to_csv("data/transactions.csv", index=False)
    print(f"Created mock transactions: {len(transactions)} records")
    return df

def create_mock_faq():
    """Create comprehensive FAQ database."""
    
    faq_data = {
        "records": [
            {
                "id": 1,
                "category": "return_policy",
                "question": "What is the return policy?",
                "answer": "Items can be returned within 30 days of purchase with original receipt. Refunds will be processed to the original payment method within 5-7 business days.",
                "keywords": ["return", "policy", "refund", "30 days"]
            },
            {
                "id": 2,
                "category": "shipping",
                "question": "Do you ship internationally?",
                "answer": "Yes, we ship to over 50 countries worldwide. International shipping typically takes 7-14 business days and costs vary by destination. Please note that customs fees may apply.",
                "keywords": ["international", "shipping", "worldwide", "customs"]
            },
            {
                "id": 3,
                "category": "payment",
                "question": "What payment methods do you accept?",
                "answer": "We accept Visa, Mastercard, American Express, PayPal, and Apple Pay. All payments are processed securely through our encrypted payment system.",
                "keywords": ["payment", "visa", "mastercard", "paypal", "apple pay"]
            },
            {
                "id": 4,
                "category": "warranty",
                "question": "What warranty do you provide?",
                "answer": "All products come with a 1-year manufacturer warranty. Extended warranty options are available for purchase. Warranty covers manufacturing defects but not physical damage.",
                "keywords": ["warranty", "1 year", "manufacturer", "defects"]
            },
            {
                "id": 5,
                "category": "product_specs",
                "question": "What are the dimensions of the Wireless Bluetooth Headphones?",
                "answer": "The Wireless Bluetooth Headphones (PRD001) measure 7.5 x 6.5 x 3 inches and weigh 0.8 lbs. They feature 40mm drivers and 20-hour battery life.",
                "keywords": ["bluetooth", "headphones", "dimensions", "PRD001", "specs"]
            },
            {
                "id": 6,
                "category": "product_specs",
                "question": "Is the Smartphone Case compatible with all phone models?",
                "answer": "The Smartphone Case (PRD002) is available in multiple sizes for iPhone and Samsung models. Please check the compatibility chart before ordering.",
                "keywords": ["smartphone", "case", "PRD002", "compatibility", "iphone", "samsung"]
            },
            {
                "id": 7,
                "category": "technical",
                "question": "How do I connect the Wireless Mouse?",
                "answer": "The Wireless Mouse (PRD005) connects via USB receiver. Insert the receiver into your computer's USB port, turn on the mouse, and it will connect automatically.",
                "keywords": ["wireless", "mouse", "PRD005", "connect", "USB"]
            },
            {
                "id": 8,
                "category": "technical",
                "question": "How long does the Power Bank take to charge?",
                "answer": "The Power Bank (PRD006) takes 4-6 hours to fully charge using the included USB-C cable. LED indicators show charging progress.",
                "keywords": ["power", "bank", "PRD006", "charge", "USB-C", "LED"]
            },
            {
                "id": 9,
                "category": "account",
                "question": "How do I track my order?",
                "answer": "You can track your order using the tracking number sent to your email. Visit our website and enter your order number and email address in the tracking section.",
                "keywords": ["track", "order", "tracking number", "email"]
            },
            {
                "id": 10,
                "category": "account",
                "question": "Can I change my shipping address after ordering?",
                "answer": "Shipping address can only be changed within 2 hours of placing the order. Contact customer support immediately if you need to make changes.",
                "keywords": ["shipping", "address", "change", "2 hours", "contact support"]
            }
        ]
    }
    
    # Save FAQ data
    with open("data/faq.json", "w", encoding="utf-8") as f:
        json.dump(faq_data, f, indent=2, ensure_ascii=False)
    
    print(f"Created FAQ database: {len(faq_data['records'])} records")
    return faq_data

def main():
    """Generate all mock data."""
    print("Generating mock data for Customer Support AI...")
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    # Generate mock data
    transactions_df = create_mock_transactions()
    faq_data = create_mock_faq()
    
    print("\nMock Data Summary:")
    print(f"- Transactions: {len(transactions_df)} records")
    print(f"- FAQ entries: {len(faq_data['records'])} records")
    print(f"- Unique products: {transactions_df['StockCode'].nunique()}")
    print(f"- Unique customers: {transactions_df['CustomerID'].nunique()}")
    
    print("\nMock data generation completed!")
    print("Files created:")
    print("  - data/transactions.csv")
    print("  - data/faq.json")

if __name__ == "__main__":
    main()