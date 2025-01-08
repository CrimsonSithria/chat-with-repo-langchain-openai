#!/usr/bin/env python3

from chat import CodeChat
import os

def main():
    print("🔄 Initializing chat...")
    
    # Create indices directory if it doesn't exist
    os.makedirs("indices", exist_ok=True)
    
    # Initialize chat
    chat = CodeChat()
    
    try:
        chat.chat_loop()
    except KeyboardInterrupt:
        print("\n👋 Goodbye! Thanks for using Code Chat!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main() 