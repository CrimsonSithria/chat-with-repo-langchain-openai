from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from pathlib import Path

@dataclass
class SymbolReference:
    """Represents a reference to a symbol in the code"""
    name: str
    file_path: Path
    line: int
    column: int
    is_definition: bool
    symbol_type: str  # 'class', 'function', 'variable', etc.

@dataclass
class ImportInfo:
    """Represents an import statement"""
    source_file: Path
    imported_module: str
    imported_symbols: List[str]
    line: int
    is_default: bool
    alias: Optional[str] = None

@dataclass
class ClassInfo:
    """Represents a class definition and its relationships"""
    name: str
    file_path: Path
    base_classes: List[str]
    methods: List[str]
    properties: List[str]
    doc_string: Optional[str] = None

class MetadataTracker:
    """Tracks code metadata including symbols, imports, and class hierarchies"""
    
    def __init__(self):
        self.symbols: Dict[str, List[SymbolReference]] = {}
        self.imports: Dict[Path, List[ImportInfo]] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.callers: Dict[str, Set[str]] = {}  # function -> set of functions that call it
        self.callees: Dict[str, Set[str]] = {}  # function -> set of functions it calls
        
    def add_symbol_reference(self, ref: SymbolReference):
        """Add a symbol reference"""
        if ref.name not in self.symbols:
            self.symbols[ref.name] = []
        self.symbols[ref.name].append(ref)
        
    def add_import(self, imp: ImportInfo):
        """Add an import statement"""
        if imp.source_file not in self.imports:
            self.imports[imp.source_file] = []
        self.imports[imp.source_file].append(imp)
        
    def add_class(self, class_info: ClassInfo):
        """Add class information"""
        self.classes[class_info.name] = class_info
        
    def add_call_relationship(self, caller: str, callee: str):
        """Add a caller/callee relationship between functions"""
        if caller not in self.callers:
            self.callers[caller] = set()
        if callee not in self.callees:
            self.callees[callee] = set()
            
        self.callers[caller].add(callee)
        self.callees[callee].add(caller)
        
    def get_symbol_references(self, name: str) -> List[SymbolReference]:
        """Get all references to a symbol"""
        return self.symbols.get(name, [])
        
    def get_class_hierarchy(self, class_name: str) -> List[str]:
        """Get the inheritance hierarchy for a class"""
        hierarchy = []
        current = class_name
        
        while current in self.classes:
            hierarchy.append(current)
            base_classes = self.classes[current].base_classes
            if not base_classes:
                break
            current = base_classes[0]  # For simplicity, just follow first base class
            
            # Prevent infinite loops from circular inheritance
            if current in hierarchy:
                break
                
        return hierarchy
        
    def get_callers(self, function_name: str) -> Set[str]:
        """Get all functions that call the given function"""
        return self.callers.get(function_name, set())
        
    def get_callees(self, function_name: str) -> Set[str]:
        """Get all functions called by the given function"""
        return self.callees.get(function_name, set())
        
    def get_module_dependencies(self, file_path: Path) -> List[str]:
        """Get all modules imported by the given file"""
        imports = self.imports.get(file_path, [])
        return [imp.imported_module for imp in imports] 