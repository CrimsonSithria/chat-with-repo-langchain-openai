class SmartChunker:
    def __init__(self, max_tokens: int = 1500):
        self.max_tokens = max_tokens
        self.language_markers = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.m': 'objective-c',
            '.mm': 'objective-c++',
        }
        
    def chunk_code(self, content: str) -> List[Tuple[str, int, int]]:
        """Chunk code content into smaller pieces with line numbers."""
        try:
            # Split content into lines
            lines = content.split('\n')
            chunks = []
            current_chunk = []
            current_chunk_start = 1  # 1-based line numbering
            
            for i, line in enumerate(lines, 1):
                current_chunk.append(line)
                
                # Check if we should create a new chunk
                if len('\n'.join(current_chunk)) >= self.max_tokens:
                    # Add the current chunk
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append((chunk_text, current_chunk_start, i))
                    
                    # Start a new chunk
                    current_chunk = []
                    current_chunk_start = i + 1
            
            # Add the last chunk if there's anything left
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                chunks.append((chunk_text, current_chunk_start, len(lines)))
            
            return chunks
            
        except Exception as e:
            print(f"Error chunking code: {str(e)}")
            return [] 