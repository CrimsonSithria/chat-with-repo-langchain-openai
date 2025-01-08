import os
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict
from ingest import CodeIngester

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeChat:
    def __init__(self, ingester: CodeIngester = None):
        self.ingester = ingester or CodeIngester()
        
    def search_similar(self, query: str, k: int = 3) -> List[Dict]:
        """Search for code chunks similar to the query."""
        query_embedding = self.ingester.get_embedding(query)
        D, I = self.ingester.index.search(query_embedding.reshape(1, -1), k)
        
        results = []
        for i, idx in enumerate(I[0]):
            if idx < len(self.ingester.metadata):
                result = self.ingester.metadata[idx].copy()
                result['distance'] = float(D[0][i])
                results.append(result)
        return results
    
    def get_chat_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Get chat response using OpenAI."""
        context = "\n\n".join(chunk["content"] for chunk in context_chunks)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful code assistant. Answer questions about the code based on the context provided."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error getting chat response: {e}"
    
    def chat_loop(self):
        """Main chat loop."""
        print("Welcome to Code Chat! Type 'exit' to quit, 'reload' to refresh codebase, or 'help' for commands.")
        
        while True:
            query = input("\nYou: ").strip()
            
            if query.lower() == 'exit':
                print("Goodbye!")
                break
            elif query.lower() == 'help':
                print("\nAvailable commands:")
                print("- exit: Quit the chat")
                print("- reload: Reload the codebase")
                print("- help: Show this help message")
                continue
            elif query.lower() == 'reload':
                print("Reloading codebase...")
                self.ingester = CodeIngester()
                self.ingester.process_directory(".")
                print("Reload complete!")
                continue
            
            # Get similar code chunks
            similar_chunks = self.search_similar(query)
            
            if not similar_chunks:
                print("No relevant code found.")
                continue
            
            # Get and print the response
            response = self.get_chat_response(query, similar_chunks)
            print("\nAssistant:", response)

if __name__ == "__main__":
    # Initialize and run the chat
    chat = CodeChat()
    print("Processing codebase...")
    chat.ingester.process_directory(".")
    print("Processing complete! Starting chat...")
    chat.chat_loop()