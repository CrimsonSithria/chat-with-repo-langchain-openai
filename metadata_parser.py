from pathlib import Path
from typing import Optional, List, Dict, Any
import tree_sitter
from tree_sitter import Language, Parser, Tree, Node
from metadata import MetadataTracker, SymbolReference, ImportInfo, ClassInfo

class MetadataParser:
    """Parses source code to extract metadata using tree-sitter"""
    
    def __init__(self):
        # Initialize tree-sitter parser
        Language.build_library(
            'build/languages.so',
            [
                'vendor/tree-sitter-python',
                'vendor/tree-sitter-javascript',
                'vendor/tree-sitter-typescript'
            ]
        )
        
        self.py_language = Language('build/languages.so', 'python')
        self.js_language = Language('build/languages.so', 'javascript')
        self.ts_language = Language('build/languages.so', 'typescript')
        
        self.parser = Parser()
        self.tracker = MetadataTracker()
        
    def _get_language(self, file_path: Path) -> Optional[Language]:
        """Get the appropriate tree-sitter language for a file"""
        ext = file_path.suffix.lower()
        if ext == '.py':
            return self.py_language
        elif ext == '.js':
            return self.js_language
        elif ext in ['.ts', '.tsx']:
            return self.ts_language
        return None
        
    def parse_file(self, file_path: Path) -> None:
        """Parse a file and extract its metadata"""
        language = self._get_language(file_path)
        if not language:
            return
            
        self.parser.set_language(language)
        
        with open(file_path) as f:
            source_code = f.read()
            
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        
        # Process the syntax tree
        self._process_node(tree.root_node, file_path, source_code)
        
    def _process_node(self, node: Node, file_path: Path, source_code: str) -> None:
        """Process a syntax tree node to extract metadata"""
        
        # Handle different node types
        if node.type == 'import_statement':
            self._process_import(node, file_path, source_code)
        elif node.type == 'class_definition':
            self._process_class(node, file_path, source_code)
        elif node.type == 'function_definition':
            self._process_function(node, file_path, source_code)
        elif node.type == 'call':
            self._process_call(node, file_path, source_code)
            
        # Process child nodes
        for child in node.children:
            self._process_node(child, file_path, source_code)
            
    def _process_import(self, node: Node, file_path: Path, source_code: str) -> None:
        """Process an import statement node"""
        module_node = next((child for child in node.children if child.type == 'string'), None)
        if not module_node:
            return
            
        imported_module = self._get_node_text(module_node, source_code).strip('"\'')
        imported_symbols = []
        is_default = False
        alias = None
        
        # Extract imported symbols based on language
        if self.parser.language == self.py_language:
            names_node = next((child for child in node.children if child.type == 'import_from_statement'), None)
            if names_node:
                imported_symbols = [
                    self._get_node_text(name, source_code)
                    for name in names_node.children
                    if name.type == 'identifier'
                ]
                
        elif self.parser.language in [self.js_language, self.ts_language]:
            import_clause = next((child for child in node.children if child.type == 'import_clause'), None)
            if import_clause:
                default_import = next((child for child in import_clause.children if child.type == 'identifier'), None)
                if default_import:
                    is_default = True
                    imported_symbols.append(self._get_node_text(default_import, source_code))
                    
                named_imports = next((child for child in import_clause.children if child.type == 'named_imports'), None)
                if named_imports:
                    for specifier in named_imports.children:
                        if specifier.type == 'import_specifier':
                            name = next((child for child in specifier.children if child.type == 'identifier'), None)
                            alias_node = next((child for child in specifier.children if child.field == 'alias'), None)
                            if name:
                                symbol = self._get_node_text(name, source_code)
                                imported_symbols.append(symbol)
                                if alias_node:
                                    alias = self._get_node_text(alias_node, source_code)
                                    
        import_info = ImportInfo(
            source_file=file_path,
            imported_module=imported_module,
            imported_symbols=imported_symbols,
            line=node.start_point[0] + 1,
            is_default=is_default,
            alias=alias
        )
        self.tracker.add_import(import_info)
        
    def _process_class(self, node: Node, file_path: Path, source_code: str) -> None:
        """Process a class definition node"""
        name_node = next((child for child in node.children if child.type == 'identifier'), None)
        if not name_node:
            return
            
        class_name = self._get_node_text(name_node, source_code)
        
        # Get base classes
        base_classes = []
        bases_node = next((child for child in node.children if child.type in ['argument_list', 'bases']), None)
        if bases_node:
            base_classes = [
                self._get_node_text(base, source_code)
                for base in bases_node.children
                if base.type == 'identifier'
            ]
            
        # Get methods and properties
        methods = []
        properties = []
        body_node = next((child for child in node.children if child.type == 'block'), None)
        if body_node:
            for child in body_node.children:
                if child.type == 'function_definition':
                    method_name = next((c for c in child.children if c.type == 'identifier'), None)
                    if method_name:
                        methods.append(self._get_node_text(method_name, source_code))
                elif child.type in ['expression_statement', 'assignment']:
                    # This is a rough approximation - would need more precise analysis for properties
                    prop_name = next((c for c in child.children if c.type == 'identifier'), None)
                    if prop_name:
                        properties.append(self._get_node_text(prop_name, source_code))
                        
        # Get docstring if present
        doc_string = None
        first_stmt = next((child for child in body_node.children if child.type == 'expression_statement'), None)
        if first_stmt:
            string_node = next((child for child in first_stmt.children if child.type == 'string'), None)
            if string_node:
                doc_string = self._get_node_text(string_node, source_code)
                
        class_info = ClassInfo(
            name=class_name,
            file_path=file_path,
            base_classes=base_classes,
            methods=methods,
            properties=properties,
            doc_string=doc_string
        )
        self.tracker.add_class(class_info)
        
        # Add class definition to symbol references
        self.tracker.add_symbol_reference(
            SymbolReference(
                name=class_name,
                file_path=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
                is_definition=True,
                symbol_type='class'
            )
        )
        
    def _process_function(self, node: Node, file_path: Path, source_code: str) -> None:
        """Process a function definition node"""
        name_node = next((child for child in node.children if child.type == 'identifier'), None)
        if not name_node:
            return
            
        function_name = self._get_node_text(name_node, source_code)
        
        # Add function definition to symbol references
        self.tracker.add_symbol_reference(
            SymbolReference(
                name=function_name,
                file_path=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
                is_definition=True,
                symbol_type='function'
            )
        )
        
    def _process_call(self, node: Node, file_path: Path, source_code: str) -> None:
        """Process a function call node"""
        # Get the caller function (we're inside its definition)
        current_function = None
        parent = node.parent
        while parent:
            if parent.type == 'function_definition':
                name_node = next((child for child in parent.children if child.type == 'identifier'), None)
                if name_node:
                    current_function = self._get_node_text(name_node, source_code)
                break
            parent = parent.parent
            
        if not current_function:
            return
            
        # Get the called function name
        func_node = next((child for child in node.children if child.type in ['identifier', 'attribute']), None)
        if not func_node:
            return
            
        called_function = self._get_node_text(func_node, source_code)
        
        # Add the caller/callee relationship
        self.tracker.add_call_relationship(current_function, called_function)
        
        # Add reference to the called function
        self.tracker.add_symbol_reference(
            SymbolReference(
                name=called_function,
                file_path=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
                is_definition=False,
                symbol_type='function'
            )
        )
        
    def _get_node_text(self, node: Node, source_code: str) -> str:
        """Get the source text for a node"""
        return source_code[node.start_byte:node.end_byte] 