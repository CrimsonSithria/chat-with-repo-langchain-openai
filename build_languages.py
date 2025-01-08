from tree_sitter import Language
import os
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and print its output."""
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if process.stdout:
            print(process.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    # Create build directory
    build_dir = Path('build')
    build_dir.mkdir(exist_ok=True)
    
    # Create vendor directory if it doesn't exist
    vendor_dir = Path('vendor')
    vendor_dir.mkdir(exist_ok=True)
    
    # Define language repositories
    repositories = {
        'python': 'https://github.com/tree-sitter/tree-sitter-python',
        'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
        'typescript': 'https://github.com/tree-sitter/tree-sitter-typescript'
    }
    
    # Clone and build each language
    for lang, repo in repositories.items():
        lang_dir = vendor_dir / f'tree-sitter-{lang}'
        
        # Clone repository if it doesn't exist
        if not lang_dir.exists():
            print(f"\nCloning {lang} grammar...")
            if not run_command(f'git clone {repo} {lang_dir}'):
                print(f"Failed to clone {lang} grammar")
                continue
        
        # Build the parser
        print(f"\nBuilding {lang} parser...")
        if not run_command('npm install', cwd=lang_dir):
            print(f"Failed to install dependencies for {lang}")
            continue
            
        # Special handling for TypeScript which has multiple parsers
        if lang == 'typescript':
            parser_dirs = [lang_dir / 'typescript', lang_dir / 'tsx']
        else:
            parser_dirs = [lang_dir]
            
        for parser_dir in parser_dirs:
            if not run_command('npm install', cwd=parser_dir):
                print(f"Failed to install dependencies for {parser_dir}")
                continue
                
            if not run_command('npx tree-sitter generate', cwd=parser_dir):
                print(f"Failed to generate parser for {parser_dir}")
                continue
                
            try:
                Language.build_library(
                    # Store the library in the `build` directory
                    str(build_dir / f'{lang}.so'),
                    # Include one or more languages
                    [str(parser_dir)]
                )
                print(f"Successfully built {lang} parser")
            except Exception as e:
                print(f"Error building {lang} parser: {e}")

if __name__ == '__main__':
    main() 