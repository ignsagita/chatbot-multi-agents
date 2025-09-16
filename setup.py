#!/usr/bin/env python3
"""
Quick Setup script for Customer Support AI System to initialize the project structure and mock data.
"""

import os
import sys

def create_directory_structure():
    """Create the required directory structure."""
    directories = [
        "data",
        "utils",
        "agents"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
        # Create __init__.py files for Python packages
        if directory in ["utils", "agents"]:
            init_file = os.path.join(directory, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write("# Customer Support AI System\n")
    
    print("Directory structure created!!")

def create_env_template():
    """Create .env template file"""
    env_content = """# Customer Support AI Configuration
# Replace with your actual OpenAI API key
OPENAI_API_KEY=your-openai-api-key-here

OPENAI_MODEL=gpt-3.5-turbo
MAX_TOKENS=150
TEMPERATURE=0.1
"""
    
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(env_content)
        print(".env template created - please add your OpenAI API key")
    else:
        print(".env file already exists")

def main():
    """Main setup function."""
    print("Setting up the system!!")
    print("=" * 50)
    
    # Create directory structure
    create_directory_structure()
    
    # Create .env template
    create_env_template()
    
    # Run mock data generation
    try:
        from create_mock_data import main as create_data
        create_data()
    except ImportError:
        print("Mock data script not found. Please run create_mock_data.py separately.")
    
    print("\n" + "=" * 50)
    print("Setup completed!!")
    print("\n Next steps:")
    print("1. Add your OpenAI API key to the .env file (if needed)")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the app: streamlit run app.py")
    print("\nMock data includes:")
    print("- 20 sample transactions")
    print("- 10 FAQ entries")
    print("- SQLite database for session management")

if __name__ == "__main__":
    main()