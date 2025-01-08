#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
from chat import CodeChat

def print_welcome():
    """Print welcome message and instructions."""
    print("""
🤖 Code Chat - Chat with your Repository
======================================

Available commands:
- help     : Show this help message
- reload   : Reload and reprocess the codebase
- exit/quit: Exit the program

Tips:
- Ask questions about code functionality
- Inquire about specific functions or classes
- Ask about implementation details
- Request explanations of code patterns
    """)

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OpenAI API key not found!")
        print("Please set your OPENAI_API_KEY in the .env file")
        sys.exit(1)
    
    # Initialize chat
    print("🔄 Initializing chat...")
    try:
        chat = CodeChat()
        directory = input("Enter the directory path to analyze (press Enter for current directory '.'): ").strip()
        if not directory:
            directory = "."
        
        if not os.path.exists(directory):
            print(f"❌ Error: Directory '{directory}' does not exist.")
            sys.exit(1)
        
        print(f"📂 Analyzing directory: {directory}")
        chat.ingester.process_directory(directory)
        print("✅ Initialization complete!")
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        sys.exit(1)
    
    # Print welcome message
    print_welcome()
    
    # Start chat loop
    try:
        chat.chat_loop()
    except KeyboardInterrupt:
        print("\n👋 Goodbye! Thanks for using Code Chat!")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 