import os
import pickle
import numpy as np
import faiss
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from smart_chunker import SmartChunker

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CodeIngester:
    """
    CodeIngester handles the processing and indexing of code files.
    Uses SmartChunker for intelligent code chunking based on AST parsing.
    """
    
    def __init__(self, chunk_size: int = 1500):
        self.chunk_size = chunk_size
        self.dimension = 1536  # OpenAI embedding dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata: List[Dict] = []
        self.indices_dir = "backend/indices"
        self.current_index_name = None
        self.smart_chunker = SmartChunker(max_tokens=chunk_size)
            
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
        """Save FAISS index and metadata to disk."""
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
        """Process a single file using smart chunking."""
        try:
            logger.info(f"Processing file: {file_path}")
            # Use SmartChunker to get intelligent chunks
            chunks = self.smart_chunker.chunk_file(file_path)
            
            if not chunks:  # Fallback to basic chunking if smart chunking fails
                logger.warning(f"Smart chunking failed for {file_path}, falling back to basic chunking")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    logger.warning(f"Skipping empty file: {file_path}")
                    return
                    
                # Basic chunking as fallback
                chunks = [{
                    'content': content[i:i + self.chunk_size],
                    'file_path': file_path,
                    'type': 'text',
                    'start_pos': i,
                    'end_pos': min(i + self.chunk_size, len(content))
                } for i in range(0, len(content), self.chunk_size)]
            
            # Process chunks and add to index
            logger.info(f"Generated {len(chunks)} chunks for {file_path}")
            for i, chunk in enumerate(chunks, 1):
                logger.debug(f"Processing chunk {i}/{len(chunks)} for {file_path}")
                embedding = self.get_embedding(chunk['content'])
                self.index.add(embedding.reshape(1, -1))
                self.metadata.append(chunk)
            logger.info(f"Successfully processed {file_path}")
                    
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def process_directory(self, directory: str):
        """Process all files in a directory."""
        try:
            logger.info(f"Starting to process directory: {directory}")
            files_processed = 0
            files_skipped = 0
            
            for root, _, files in os.walk(directory):
                for file in files:
                    # Skip hidden files and certain directories
                    if file.startswith('.') or 'node_modules' in root or 'venv' in root:
                        files_skipped += 1
                        continue
                    
                    # Process only supported file types
                    if os.path.splitext(file)[1] in self.smart_chunker.language_markers:
                        file_path = os.path.join(root, file)
                        self.process_file(file_path)
                        files_processed += 1
                    else:
                        files_skipped += 1
            
            logger.info(f"Directory processing complete. Processed {files_processed} files, skipped {files_skipped} files.")
                        
        except Exception as e:
            logger.error(f"Failed to process directory: {e}")
            raise 