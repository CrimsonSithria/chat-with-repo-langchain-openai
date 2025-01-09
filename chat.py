import os
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Tuple
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
            # Only create a new ingester if we don't have one or if it's for a different index
            if not hasattr(self, 'current_index') or self.current_index != index_name:
                print(f"Loading existing index: {index_name}")
                self.ingester = CodeIngester()
                # Load existing state
                success = self.ingester.load_state(index_name)
                if success:
                    self.current_index = index_name
                return success
            return True
        except Exception as e:
            print(f"Error loading index {index_name}: {e}")
            return False
    
    def create_new_index(self, directory: str, name: str) -> bool:
        """Create a new index from a directory."""
        try:
            print(f"\nDEBUG: Creating new index for directory: {directory}")
            print(f"DEBUG: Index name: {name}")
            
            # Create new ingester
            self.ingester = CodeIngester()
            
            # Process directory
            print("DEBUG: Processing directory...")
            self.ingester.process_directory(directory)
            print(f"DEBUG: Found {len(self.ingester.metadata)} files to index")
            
            # Save state
            print("DEBUG: Saving index state...")
            success = self.ingester.save_state(name)
            if success:
                print("DEBUG: Successfully created and saved index")
                self.current_index = name
                return True
            else:
                print("DEBUG: Failed to save index state")
                return False
                
        except Exception as e:
            print(f"DEBUG: Error creating index: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def search_similar(self, query: str, initial_k: int = 30) -> List[Dict]:
        """Search for code chunks similar to the query, maximizing context within token limits."""
        print(f"\nDEBUG: Starting search_similar with query: {query}")
        
        # Check if index is empty
        if self.ingester.index.ntotal == 0:
            print("DEBUG: Index is empty - no code has been indexed yet")
            return []
            
        # Get query embedding
        query_embedding = self.ingester.get_embedding(query)
        
        # Limit k to the number of vectors in the index
        k = min(initial_k, self.ingester.index.ntotal)
        print(f"DEBUG: Searching among {self.ingester.index.ntotal} vectors with k={k}")
        
        # Perform search
        D, I = self.ingester.index.search(query_embedding.reshape(1, -1), k)
        print(f"DEBUG: Found {len(I[0])} matches")
        
        results = []
        total_tokens = 0
        system_prompt = """You are a helpful code assistant. Analyze the code context and provide clear, detailed explanations.
Focus on:
1. Code structure and relationships
2. Implementation details and patterns
3. Key functionality and purpose
4. Dependencies and interactions
Use markdown formatting for code snippets and explanations."""

        system_prompt_tokens = self.count_tokens(system_prompt)
        query_tokens = self.count_tokens(query)
        available_tokens = self.max_tokens - system_prompt_tokens - query_tokens - self.max_response_tokens - 500  # Buffer for safety
        
        print(f"DEBUG: Token budget calculation:")
        print(f"- Max tokens: {self.max_tokens}")
        print(f"- System prompt tokens: {system_prompt_tokens}")
        print(f"- Query tokens: {query_tokens}")
        print(f"- Response tokens reserved: {self.max_response_tokens}")
        print(f"- Available for chunks: {available_tokens}")
        
        # Group chunks by file to maintain context
        file_chunks: Dict[str, List[Dict]] = {}
        
        for i, idx in enumerate(I[0]):
            if idx < len(self.ingester.metadata):
                result = self.ingester.metadata[idx].copy()
                result['distance'] = float(D[0][i])
                file_path = result.get("file", "unknown")
                print(f"\nDEBUG: Processing chunk from file: {file_path}")
                print(f"- Distance: {result['distance']}")
                print(f"- Content length: {len(result.get('content', ''))}")
                
                if file_path not in file_chunks:
                    file_chunks[file_path] = []
                file_chunks[file_path].append(result)
        
        # Sort chunks within each file by line number
        for file_path, chunks in file_chunks.items():
            print(f"\nDEBUG: Processing file: {file_path}")
            print(f"- Number of chunks: {len(chunks)}")
            
            chunks.sort(key=lambda x: x.get("start_line", 0))
            
            # Add chunks while respecting token limit
            for chunk in chunks:
                chunk_tokens = self.count_tokens(chunk["content"])
                print(f"DEBUG: Chunk token count: {chunk_tokens}")
                if total_tokens + chunk_tokens <= available_tokens:
                    results.append(chunk)
                    total_tokens += chunk_tokens
                    print(f"- Added chunk (total tokens now: {total_tokens})")
                else:
                    print(f"- Skipped chunk (would exceed token limit)")
                    break
        
        print(f"\nDEBUG: Final results:")
        print(f"- Number of chunks: {len(results)}")
        print(f"- Total tokens: {total_tokens}")
        
        return results
    
    def get_chat_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Get chat response using OpenAI."""
        # Organize context by files
        file_contexts = {}
        for chunk in context_chunks:
            file_path = chunk.get("file", "unknown")
            if file_path not in file_contexts:
                file_contexts[file_path] = []
            file_contexts[file_path].append(chunk)
        
        # Build structured context
        context_parts = []
        for file_path, chunks in file_contexts.items():
            chunks.sort(key=lambda x: x.get("start_line", 0))
            context_parts.append(f"\nFile: {file_path}")
            for chunk in chunks:
                context_parts.append(f"Lines {chunk.get('start_line', '?')}-{chunk.get('end_line', '?')}:")
                context_parts.append("```python")
                context_parts.append(chunk["content"].strip())
                context_parts.append("```\n")
        
        context = "\n".join(context_parts)
        
        system_prompt = """You are a highly knowledgeable code assistant with expertise in Python and software architecture.
Your task is to analyze code and provide clear, detailed explanations.

When analyzing code, focus on:
1. Code Structure:
   - Class hierarchies and relationships
   - Module organization and dependencies
   - Function interactions and call patterns

2. Implementation Details:
   - Key algorithms and data structures
   - Design patterns and best practices
   - Error handling and edge cases

3. Functionality:
   - Main purpose of each component
   - How different parts work together
   - Input/output behavior

4. Code Quality:
   - Potential improvements or optimizations
   - Adherence to best practices
   - Error handling and robustness

Format your responses using markdown:
- Use headings for main sections
- Use bullet points for lists
- Use code blocks for code examples
- Use bold/italic for emphasis

Keep your explanations clear and concise, but include all relevant technical details."""
        
        try:
            response = client.chat.completions.create(
                model="o1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a detailed analysis focusing on the aspects most relevant to the question."}
                ],
                max_completion_tokens=self.max_response_tokens,
                reasoning_effort="high",
            )
            
            # Print token usage information
            usage = response.usage
            print("\nToken Usage:")
            print(f"- Prompt tokens: {usage.prompt_tokens}")
            print(f"- Completion tokens: {usage.completion_tokens}")
            print(f"- Total tokens: {usage.total_tokens}")
            if hasattr(usage, 'completion_tokens_details'):
                print(f"- Reasoning tokens: {usage.completion_tokens_details.reasoning_tokens}")
            
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
                print("r. Analyze Root Folder")
                print("q. Quit")
                
                choice = input("\nSelect an option: ").strip().lower()
                
                if choice == 'q':
                    return 'quit'
                elif choice == 'r':
                    # Directly analyze root folder
                    name = "root"
                    if self.create_new_index(".", name):
                        print(f"Successfully created index for root folder")
                        return name
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
            print("r. Analyze Root Folder")
            print("q. Quit")
            
            choice = input("\nSelect an option: ").strip().lower()
            
            if choice == 'q':
                return 'quit'
            elif choice == 'r':
                # Directly analyze root folder
                name = "root"
                if self.create_new_index(".", name):
                    print(f"Successfully created index for root folder")
                    return name
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

    async def get_response(self, message: str) -> Tuple[str, Dict[str, int]]:
        """Get a response from the chat model and return both the response and token usage."""
        try:
            # Get similar chunks
            similar_chunks = self.search_similar(message)
            
            # Get chat response
            response = await self.get_chat_response(message, similar_chunks)
            
            # Get token usage from the last response
            token_usage = {
                'prompt': response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                'completion': response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                'total': response.usage.total_tokens if hasattr(response, 'usage') else 0,
                'reasoning': len(response.content.split()) if hasattr(response, 'content') else 0  # Approximate
            }
            
            return response.content if hasattr(response, 'content') else str(response), token_usage
            
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            raise

if __name__ == "__main__":
    # Initialize and run the chat
    chat = CodeChat()
    chat.chat_loop()