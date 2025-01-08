import os
from typing import List, Dict, Any, Optional
import tiktoken

class SmartChunker:
    """
    Intelligent code chunking system based on CintraAI's implementation.
    Focuses on semantic chunking without direct tree-sitter dependency.
    """
    
    def __init__(self, max_tokens: int = 1000):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Supported file extensions and their markers
        self.language_markers = {
            '.py': ['def ', 'class ', '@', 'import ', 'from '],
            '.js': ['function ', 'class ', 'import ', 'export ', 'const ', 'let '],
            '.ts': ['function ', 'class ', 'interface ', 'type ', 'import ', 'export '],
            '.jsx': ['function ', 'class ', 'import ', 'export ', 'const ', 'let '],
            '.tsx': ['function ', 'class ', 'interface ', 'type ', 'import ', 'export ']
        }
        
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
        
    def _find_chunk_boundaries(self, content: str, file_ext: str) -> List[Dict[str, Any]]:
        """Find natural boundaries for chunks based on code structure."""
        markers = self.language_markers.get(file_ext, [])
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        def create_chunk(lines_list, chunk_type="code"):
            if not lines_list:
                return None
            chunk_content = '\n'.join(lines_list)
            return {
                'content': chunk_content,
                'type': chunk_type,
                'tokens': self._count_tokens(chunk_content)
            }
        
        for line in lines:
            line_stripped = line.strip()
            is_boundary = any(line_stripped.startswith(marker) for marker in markers)
            line_tokens = self._count_tokens(line + '\n')
            
            # Start new chunk if:
            # 1. Current line is a boundary (function/class definition etc.)
            # 2. Adding this line would exceed token limit
            if (is_boundary and current_chunk) or \
               (current_tokens + line_tokens > self.max_tokens and current_chunk):
                chunk = create_chunk(current_chunk)
                if chunk:
                    chunks.append(chunk)
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(line)
            current_tokens += line_tokens
        
        # Add remaining lines as final chunk
        if current_chunk:
            chunk = create_chunk(current_chunk)
            if chunk:
                chunks.append(chunk)
        
        return chunks
        
    def chunk_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a file and return intelligent chunks."""
        try:
            file_ext = os.path.splitext(file_path)[1]
            if file_ext not in self.language_markers:
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                return []
                
            chunks = self._find_chunk_boundaries(content, file_ext)
            
            # Add file metadata to chunks
            for chunk in chunks:
                chunk['file_path'] = file_path
                chunk['language'] = file_ext[1:]  # Remove dot from extension
                
            return chunks
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return []
            
    def chunk_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Process all supported files in a directory."""
        all_chunks = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1] in self.language_markers:
                    file_path = os.path.join(root, file)
                    chunks = self.chunk_file(file_path)
                    all_chunks.extend(chunks)
                    
        return all_chunks 