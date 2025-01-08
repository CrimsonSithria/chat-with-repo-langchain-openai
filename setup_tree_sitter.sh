#!/bin/bash

# Create directories
mkdir -p vendor build

# Clone tree-sitter grammars
cd vendor

# Python grammar
if [ ! -d "tree-sitter-python" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-python.git
fi

# JavaScript grammar
if [ ! -d "tree-sitter-javascript" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-javascript.git
fi

# TypeScript grammar
if [ ! -d "tree-sitter-typescript" ]; then
    git clone https://github.com/tree-sitter/tree-sitter-typescript.git
fi

cd ..

# Build languages
python build_languages.py

echo "Tree-sitter setup complete!" 