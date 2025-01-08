from pathlib import Path
from typing import List, Set, Dict, Optional
from metadata import MetadataTracker
from metadata_parser import MetadataParser
import logging

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes code and provides insights using the metadata system"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.parser = MetadataParser()
        self.tracker = self.parser.tracker
        
    def analyze_codebase(self, file_patterns: List[str] = None) -> None:
        """Analyze all code files in the codebase"""
        if file_patterns is None:
            file_patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.tsx']
            
        for pattern in file_patterns:
            for file_path in self.root_dir.glob(pattern):
                try:
                    logger.info(f"Analyzing {file_path}")
                    self.parser.parse_file(file_path)
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {str(e)}")
                    
    def get_symbol_info(self, symbol_name: str) -> Dict:
        """Get comprehensive information about a symbol"""
        refs = self.tracker.get_symbol_references(symbol_name)
        if not refs:
            return {}
            
        # Get the definition if it exists
        definition = next((ref for ref in refs if ref.is_definition), None)
        
        # Get all usages
        usages = [ref for ref in refs if not ref.is_definition]
        
        info = {
            'name': symbol_name,
            'type': refs[0].symbol_type if refs else None,
            'definition': {
                'file': str(definition.file_path.relative_to(self.root_dir)),
                'line': definition.line,
                'column': definition.column
            } if definition else None,
            'usages': [
                {
                    'file': str(ref.file_path.relative_to(self.root_dir)),
                    'line': ref.line,
                    'column': ref.column
                }
                for ref in usages
            ]
        }
        
        # Add class-specific information
        if refs[0].symbol_type == 'class':
            class_info = self.tracker.classes.get(symbol_name)
            if class_info:
                info.update({
                    'hierarchy': self.tracker.get_class_hierarchy(symbol_name),
                    'methods': class_info.methods,
                    'properties': class_info.properties,
                    'doc_string': class_info.doc_string
                })
                
        # Add function-specific information
        elif refs[0].symbol_type == 'function':
            info.update({
                'callers': list(self.tracker.get_callers(symbol_name)),
                'calls': list(self.tracker.get_callees(symbol_name))
            })
            
        return info
        
    def get_file_dependencies(self, file_path: Path) -> Dict:
        """Get dependency information for a file"""
        rel_path = file_path.relative_to(self.root_dir)
        imports = self.tracker.imports.get(file_path, [])
        
        return {
            'file': str(rel_path),
            'imports': [
                {
                    'module': imp.imported_module,
                    'symbols': imp.imported_symbols,
                    'line': imp.line,
                    'is_default': imp.is_default,
                    'alias': imp.alias
                }
                for imp in imports
            ],
            'imported_by': [
                str(file.relative_to(self.root_dir))
                for file, imps in self.tracker.imports.items()
                if any(imp.imported_module == str(rel_path) for imp in imps)
            ]
        }
        
    def get_class_hierarchy_graph(self) -> Dict[str, List[str]]:
        """Get a graph of all class inheritance relationships"""
        graph = {}
        for class_name, class_info in self.tracker.classes.items():
            graph[class_name] = class_info.base_classes
        return graph
        
    def get_call_graph(self) -> Dict[str, List[str]]:
        """Get a graph of all function call relationships"""
        graph = {}
        for caller, callees in self.tracker.callees.items():
            graph[caller] = list(callees)
        return graph
        
    def get_module_dependencies_graph(self) -> Dict[str, List[str]]:
        """Get a graph of module dependencies"""
        graph = {}
        for file_path in self.tracker.imports:
            rel_path = str(file_path.relative_to(self.root_dir))
            graph[rel_path] = self.tracker.get_module_dependencies(file_path)
        return graph
        
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the module import graph"""
        graph = self.get_module_dependencies_graph()
        visited = set()
        path = []
        cycles = []
        
        def dfs(module: str) -> None:
            if module in path:
                cycle_start = path.index(module)
                cycles.append(path[cycle_start:])
                return
                
            if module in visited:
                return
                
            visited.add(module)
            path.append(module)
            
            for dep in graph.get(module, []):
                dfs(dep)
                
            path.pop()
            
        for module in graph:
            if module not in visited:
                dfs(module)
                
        return cycles
        
    def find_unused_symbols(self) -> List[Dict]:
        """Find symbols that are defined but never used"""
        unused = []
        for name, refs in self.tracker.symbols.items():
            definition = next((ref for ref in refs if ref.is_definition), None)
            if definition and len(refs) == 1:  # Only the definition exists
                unused.append({
                    'name': name,
                    'type': definition.symbol_type,
                    'file': str(definition.file_path.relative_to(self.root_dir)),
                    'line': definition.line
                })
        return unused 