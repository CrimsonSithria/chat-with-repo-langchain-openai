import os
import pickle
import numpy as np
import faiss
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeIngester:
    def __init__(self, chunk_size: int = 1500):
        self.chunk_size = chunk_size
        self.dimension = 1536  # OpenAI embedding dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata: List[Dict] = []
        self.indices_dir = "indices"
        self.current_index_name = None
        
    def get_index_path(self, index_name: str) -> tuple[str, str]:
        """Get paths for index and metadata files."""
        os.makedirs(self.indices_dir, exist_ok=True)
        return (
            os.path.join(self.indices_dir, f"{index_name}.index"),
            os.path.join(self.indices_dir, f"{index_name}.pkl")
        )
        
    def list_available_indices(self) -> List[str]:
        """List all available indexed codebases."""
        if not os.path.exists(self.indices_dir):
            return []
        indices = []
        for file in os.listdir(self.indices_dir):
            if file.endswith('.index'):
                indices.append(file[:-6])  # Remove .index extension
        return indices
        
    def save_state(self, index_name: str):
        """Save the FAISS index and metadata to disk."""
        try:
            index_file, metadata_file = self.get_index_path(index_name)
            faiss.write_index(self.index, index_file)
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            self.current_index_name = index_name
        except Exception as e:
            raise Exception(f"Failed to save index: {e}")
            
    def load_state(self, index_name: str):
        """Load a FAISS index and metadata from disk."""
        try:
            index_file, metadata_file = self.get_index_path(index_name)
            if not os.path.exists(index_file) or not os.path.exists(metadata_file):
                raise FileNotFoundError(f"Index {index_name} not found")
                
            self.index = faiss.read_index(index_file)
            with open(metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            self.current_index_name = index_name
        except Exception as e:
            raise Exception(f"Failed to load index: {e}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text."""
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            raise Exception(f"Failed to get embedding: {e}")
    
    def process_file(self, file_path: str):
        """Process a single file and add its chunks to the index."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return
            
            # Simple chunking by size
            chunks = [content[i:i + self.chunk_size] 
                     for i in range(0, len(content), self.chunk_size)]
            
            for chunk in chunks:
                # Get embedding
                embedding = self.get_embedding(chunk)
                
                # Add to FAISS index
                self.index.add(embedding.reshape(1, -1))
                
                # Store metadata
                self.metadata.append({
                    "content": chunk,
                    "file_path": file_path,
                    "start_pos": chunks.index(chunk) * self.chunk_size,
                    "end_pos": min((chunks.index(chunk) + 1) * self.chunk_size, len(content))
                })
                
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
    
    def process_directory(self, directory: str):
        """Process all files in a directory."""
        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    # Skip hidden files and certain directories
                    if file.startswith('.') or 'node_modules' in root or 'venv' in root:
                        continue
                    
                    # Process only text files
                    if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.md', '.txt')):
                        file_path = os.path.join(root, file)
                        self.process_file(file_path)
                        
        except Exception as e:
            raise Exception(f"Failed to process directory: {e}") 