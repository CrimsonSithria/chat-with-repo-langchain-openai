import os
import glob
from typing import List, Dict
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI

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
    
    def read_file(self, file_path: str) -> str:
        """Read a file and return its content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""
    
    def chunk_content(self, content: str) -> List[str]:
        """Split content into chunks of approximately chunk_size."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line.split())
            if current_size + line_size > self.chunk_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text."""
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return np.array(response.data[0].embedding, dtype='float32')
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return np.zeros(self.dimension, dtype='float32')
    
    def process_file(self, file_path: str) -> None:
        """Process a single file: read, chunk, embed, and index."""
        content = self.read_file(file_path)
        if not content:
            return
        
        chunks = self.chunk_content(content)
        for chunk in chunks:
            embedding = self.get_embedding(chunk)
            self.index.add(embedding.reshape(1, -1))
            self.metadata.append({
                "file_path": file_path,
                "content": chunk
            })
    
    def process_directory(self, directory: str, file_patterns: List[str] = None) -> None:
        """Process all matching files in a directory."""
        if file_patterns is None:
            file_patterns = ['**/*.py', '**/*.js', '**/*.ts']
        
        for pattern in file_patterns:
            full_pattern = os.path.join(directory, pattern)
            for file_path in glob.glob(full_pattern, recursive=True):
                print(f"Processing {file_path}")
                self.process_file(file_path)

if __name__ == "__main__":
    directory = input("Enter the directory path to analyze (press Enter for current directory '.'): ").strip()
    if not directory:
        directory = "."
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        exit(1)
    
    print(f"Analyzing directory: {directory}")
    ingester = CodeIngester()
    ingester.process_directory(directory) 