import os
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict
import tiktoken
from ingest import CodeIngester

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeChat:
    def __init__(self, ingester: CodeIngester = None):
        self.ingester = ingester or CodeIngester()
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.max_tokens = 128000  # GPT-4 Turbo max context
        self.max_response_tokens = 4096  # Reserve tokens for response
        
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self.encoding.encode(text))
    
    def list_available_indices(self) -> List[str]:
        """List all available indexed codebases."""
        return self.ingester.list_available_indices()
    
    def load_index(self, index_name: str) -> bool:
        """Load a specific index."""
        try:
            self.ingester.load_state(index_name)
            return True
        except Exception as e:
            print(f"Error loading index {index_name}: {e}")
            return False
    
    def create_new_index(self, directory: str, name: str) -> bool:
        """Create a new index from a directory."""
        try:
            self.ingester = CodeIngester()
            self.ingester.process_directory(directory)
            self.ingester.save_state(name)
            return True
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
        
    def search_similar(self, query: str, initial_k: int = 20) -> List[Dict]:
        """Search for code chunks similar to the query, maximizing context within token limits."""
        query_embedding = self.ingester.get_embedding(query)
        
        # Start with a larger k to have more candidates
        D, I = self.ingester.index.search(query_embedding.reshape(1, -1), initial_k)
        
        results = []
        total_tokens = 0
        system_prompt_tokens = self.count_tokens("You are a helpful code assistant. Answer questions about the code based on the context provided.")
        query_tokens = self.count_tokens(query)
        available_tokens = self.max_tokens - system_prompt_tokens - query_tokens - self.max_response_tokens
        
        for i, idx in enumerate(I[0]):
            if idx < len(self.ingester.metadata):
                result = self.ingester.metadata[idx].copy()
                result['distance'] = float(D[0][i])
                chunk_tokens = self.count_tokens(result["content"])
                if total_tokens + chunk_tokens <= available_tokens:
                    results.append(result)
                    total_tokens += chunk_tokens
                else:
                    break
        return results
    
    def get_chat_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Get chat response using OpenAI."""
        context = "\n\n".join(chunk["content"] for chunk in context_chunks)
        
        try:
            response = client.chat.completions.create(
                model="o1",
                messages=[
                    {"role": "developer", "content": "You are a helpful code assistant. Answer questions about the code based on the context provided."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                max_completion_tokens=self.max_response_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error getting chat response: {e}"
    
    def show_index_menu(self) -> str:
        """Show menu for index selection and return chosen index name."""
        while True:
            print("\nAvailable Indices:")
            indices = self.list_available_indices()
            
            if not indices:
                print("No indices found.")
                print("\nOptions:")
                print("n. Create New Index")
                print("q. Quit")
                
                choice = input("\nSelect an option: ").strip().lower()
                
                if choice == 'q':
                    return 'quit'
                elif choice == 'n':
                    dir_path = input("Enter directory path to index: ").strip() or "."
                    name = input("Enter name for the new index: ").strip()
                    if not name:
                        name = os.path.basename(os.path.abspath(dir_path))
                    if self.create_new_index(dir_path, name):
                        print(f"Successfully created index: {name}")
                        return name
                else:
                    print("Invalid choice. Please try again.")
                continue
            
            # Print available indices
            for i, idx in enumerate(indices, 1):
                print(f"{i}. {idx}")
            
            print("\nOptions:")
            print("n. Create New Index")
            print("q. Quit")
            
            choice = input("\nSelect an option: ").strip().lower()
            
            if choice == 'q':
                return 'quit'
            elif choice == 'n':
                dir_path = input("Enter directory path to index: ").strip() or "."
                name = input("Enter name for the new index: ").strip()
                if not name:
                    name = os.path.basename(os.path.abspath(dir_path))
                if self.create_new_index(dir_path, name):
                    print(f"Successfully created index: {name}")
                    return name
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(indices):
                    selected_index = indices[idx]
                    if self.load_index(selected_index):
                        return selected_index
                    else:
                        print("Failed to load index. Please try again.")
                else:
                    print("Invalid index number. Please try again.")
            else:
                print("Invalid choice. Please try again.")
    
    def chat_loop(self):
        """Main chat loop with index management."""
        print("Welcome to Code Chat! Type 'exit' to quit, 'switch' to change index, or 'help' for commands.")
        
        # Initial index selection
        index_name = self.show_index_menu()
        if index_name == 'quit':
            print("Goodbye!")
            return
        
        # Ensure index is loaded
        if not self.load_index(index_name):
            print("Failed to load initial index. Exiting.")
            return
            
        print(f"\nUsing index: {index_name}")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                
                if query.lower() == 'exit':
                    print("Goodbye!")
                    break
                elif query.lower() == 'help':
                    print("\nAvailable commands:")
                    print("- exit: Quit the chat")
                    print("- switch: Switch or create new index")
                    print("- help: Show this help message")
                    continue
                elif query.lower() == 'switch':
                    index_name = self.show_index_menu()
                    if index_name == 'quit':
                        print("Goodbye!")
                        break
                    if not self.load_index(index_name):
                        continue
                    print(f"Switched to index: {index_name}")
                    continue
                
                # Get similar code chunks
                similar_chunks = self.search_similar(query)
                
                if not similar_chunks:
                    print("No relevant code found.")
                    continue
                
                # Get and print the response
                response = self.get_chat_response(query, similar_chunks)
                print("\nAssistant:", response)
                
            except Exception as e:
                print(f"Error: {e}")
                print("Please try again.")

if __name__ == "__main__":
    # Initialize and run the chat
    chat = CodeChat()
    chat.chat_loop()