import os
import pickle
import numpy as np
import faiss
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import logging
import json

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
        try:
            print("\nDEBUG: Listing available indices")
            if not os.path.exists(self.indices_dir):
                print("DEBUG: Indices directory does not exist")
                return []
                
            indices = []
            for item in os.listdir(self.indices_dir):
                item_path = os.path.join(self.indices_dir, item)
                # Check if it's a directory and contains required files
                if os.path.isdir(item_path):
                    metadata_path = os.path.join(item_path, "metadata.json")
                    embeddings_path = os.path.join(item_path, "embeddings.npy")
                    if os.path.exists(metadata_path) and os.path.exists(embeddings_path):
                        indices.append(item)
                        print(f"DEBUG: Found valid index: {item}")
                # Check for legacy format
                elif item.endswith('.index'):
                    legacy_name = item[:-6]  # Remove .index extension
                    if legacy_name not in indices:  # Avoid duplicates
                        indices.append(legacy_name)
                        print(f"DEBUG: Found legacy index: {legacy_name}")
                        
            print(f"DEBUG: Found {len(indices)} indices: {indices}")
            return indices
            
        except Exception as e:
            print(f"DEBUG: Error listing indices: {str(e)}")
            return []
        
    def save_state(self, name: str):
        """Save index state to disk."""
        try:
            print(f"\nDEBUG: Saving index state for: {name}")
            
            # Validate state before saving
            if len(self.metadata) == 0 or self.index.ntotal == 0:
                print("DEBUG: No data to save - index is empty")
                return False
                
            if len(self.metadata) != self.index.ntotal:
                print("DEBUG: Metadata and index size mismatch")
                return False
            
            # Create indices directory if it doesn't exist
            os.makedirs(self.indices_dir, exist_ok=True)
            
            # Create index-specific directory
            index_dir = os.path.join(self.indices_dir, name)
            if os.path.exists(index_dir):
                print(f"DEBUG: Removing existing index directory: {index_dir}")
                import shutil
                shutil.rmtree(index_dir)
            
            os.makedirs(index_dir)
            print(f"DEBUG: Created index directory: {index_dir}")
            
            # Save metadata as JSON
            metadata_path = os.path.join(index_dir, "metadata.json")
            print(f"DEBUG: Saving metadata to: {metadata_path}")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            print(f"DEBUG: Saved {len(self.metadata)} metadata entries")
            
            # Save FAISS index
            index_path = os.path.join(index_dir, "index.faiss")
            print(f"DEBUG: Saving FAISS index to: {index_path}")
            faiss.write_index(self.index, index_path)
            print(f"DEBUG: Saved index with {self.index.ntotal} vectors")
            
            # Verify saved files
            if not os.path.exists(metadata_path) or not os.path.exists(index_path):
                print("DEBUG: Failed to verify saved files")
                return False
            
            self.current_index_name = name
            print("DEBUG: Successfully saved index state")
            return True
            
        except Exception as e:
            print(f"DEBUG: Error saving state: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_state(self, name: str) -> bool:
        """Load index state from disk."""
        try:
            print(f"\nDEBUG: Loading index state for: {name}")
            
            # Create indices directory if it doesn't exist
            os.makedirs(self.indices_dir, exist_ok=True)
            
            # Check if index directory exists
            index_dir = os.path.join(self.indices_dir, name)
            if not os.path.exists(index_dir):
                print(f"DEBUG: Index directory does not exist: {index_dir}")
                return False
                
            # Load metadata
            metadata_path = os.path.join(index_dir, "metadata.json")
            print(f"DEBUG: Loading metadata from: {metadata_path}")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                print(f"DEBUG: Loaded {len(self.metadata)} metadata entries")
            else:
                print("DEBUG: No metadata file found")
                return False
            
            # Load FAISS index
            index_path = os.path.join(index_dir, "index.faiss")
            print(f"DEBUG: Loading FAISS index from: {index_path}")
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
                print(f"DEBUG: Loaded index with {self.index.ntotal} vectors")
            else:
                print("DEBUG: No index file found")
                return False
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Error loading state: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
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
        """Process all Python files in a directory."""
        try:
            print(f"\nDEBUG: Processing directory: {directory}")
            
            # Reset state
            self.metadata = []
            self.index = faiss.IndexFlatL2(self.dimension)
            
            # Convert to absolute path and ensure directory exists
            directory = os.path.abspath(directory)
            if not os.path.exists(directory):
                print(f"DEBUG: Directory does not exist: {directory}")
                return False
                
            # Track files processed
            files_processed = 0
            files_with_content = 0
            total_chunks = 0
            
            # Walk through directory
            for root, dirs, files in os.walk(directory):
                # Skip hidden directories and common exclude patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d not in {'venv', 'env', '.git', '__pycache__', 'node_modules'}]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):  # Include more file types
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, directory)
                        
                        print(f"\nDEBUG: Processing file: {rel_path}")
                        files_processed += 1
                        
                        try:
                            # Check file size before reading
                            if os.path.getsize(file_path) == 0:
                                print(f"DEBUG: Skipping empty file: {rel_path}")
                                continue
                                
                            with open(file_path, 'r', encoding='utf-8') as f:
                                try:
                                    content = f.read().strip()
                                except UnicodeDecodeError:
                                    print(f"DEBUG: Skipping binary file: {rel_path}")
                                    continue
                                
                            if not content:
                                print(f"DEBUG: Skipping empty file: {rel_path}")
                                continue
                                
                            # Get chunks using basic line-based chunking
                            lines = content.split('\n')
                            current_chunk = []
                            current_chunk_start = 1
                            chunk_size = min(self.chunk_size, 8000)  # Limit chunk size
                            
                            for i, line in enumerate(lines, 1):
                                current_chunk.append(line)
                                chunk_text = '\n'.join(current_chunk)
                                
                                # Create new chunk when size limit reached or at end of file
                                if len(chunk_text.encode('utf-8')) >= chunk_size or i == len(lines):
                                    try:
                                        # Validate chunk content
                                        if not chunk_text.strip():
                                            continue
                                            
                                        # Get embedding
                                        embedding = self.get_embedding(chunk_text)
                                        
                                        if embedding is None or len(embedding) != self.dimension:
                                            print(f"DEBUG: Invalid embedding for chunk in {rel_path}")
                                            continue
                                            
                                        # Add to FAISS index
                                        self.index.add(embedding.reshape(1, -1))
                                        
                                        # Store metadata
                                        chunk_metadata = {
                                            "file": rel_path,
                                            "content": chunk_text,
                                            "start_line": current_chunk_start,
                                            "end_line": i,
                                            "language": os.path.splitext(file)[1][1:],
                                            "size": len(chunk_text)
                                        }
                                        
                                        self.metadata.append(chunk_metadata)
                                        total_chunks += 1
                                        
                                        print(f"DEBUG: Added chunk {total_chunks} for {rel_path} (lines {current_chunk_start}-{i})")
                                        
                                        # Reset chunk
                                        current_chunk = []
                                        current_chunk_start = i + 1
                                        
                                    except Exception as chunk_error:
                                        print(f"DEBUG: Error processing chunk in {rel_path}: {str(chunk_error)}")
                                        continue
                            
                            if total_chunks > files_processed:  # Successful chunks added
                                files_with_content += 1
                                
                        except Exception as file_error:
                            print(f"DEBUG: Error processing file {rel_path}: {str(file_error)}")
                            continue
            
            print(f"\nDEBUG: Directory processing summary:")
            print(f"- Total files found: {files_processed}")
            print(f"- Files with content: {files_with_content}")
            print(f"- Total chunks: {total_chunks}")
            print(f"- Index size: {self.index.ntotal} vectors")
            print(f"- Metadata entries: {len(self.metadata)}")
            
            # Validate final state
            if total_chunks == 0 or len(self.metadata) == 0 or self.index.ntotal == 0:
                print("DEBUG: No content was processed successfully")
                return False
                
            # Verify index integrity
            if len(self.metadata) != self.index.ntotal:
                print("DEBUG: Metadata and index size mismatch")
                return False
                
            return True
            
        except Exception as e:
            print(f"DEBUG: Error in process_directory: {str(e)}")
            import traceback
            traceback.print_exc()
            return False 