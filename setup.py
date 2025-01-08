import subprocess
import os
import sys
from pathlib import Path
import shutil

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

def check_tree_sitter_cli():
    """Check if tree-sitter CLI is installed."""
    return shutil.which('tree-sitter') is not None

def install_tree_sitter_cli():
    """Install tree-sitter CLI using npm."""
    print("\nInstalling tree-sitter CLI...")
    if not shutil.which('npm'):
        print("Error: npm is not installed. Please install Node.js and npm first.")
        print("Visit https://nodejs.org/ to download and install Node.js")
        return False
    
    return run_command('npm install -g tree-sitter-cli')

def setup_tree_sitter():
    """Set up tree-sitter and build language parsers."""
    print("\nSetting up tree-sitter...")
    
    # Check and install tree-sitter CLI if needed
    if not check_tree_sitter_cli():
        if not install_tree_sitter_cli():
            return False
    
    # Create directories
    vendor_dir = Path("vendor")
    build_dir = Path("build")
    vendor_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)
    
    # Clone repositories
    repositories = {
        "python": "https://github.com/tree-sitter/tree-sitter-python.git",
        "javascript": "https://github.com/tree-sitter/tree-sitter-javascript.git",
        "typescript": "https://github.com/tree-sitter/tree-sitter-typescript.git"
    }
    
    for name, url in repositories.items():
        repo_dir = vendor_dir / f"tree-sitter-{name}"
        if not repo_dir.exists():
            print(f"\nCloning {name} grammar...")
            if not run_command(f"git clone {url}", cwd=vendor_dir):
                print(f"Failed to clone {name} grammar")
                return False
    
    # Build languages
    print("\nBuilding language parsers...")
    if not run_command("python build_languages.py"):
        print("Failed to build language parsers")
        return False
    
    return True

def main():
    print("Setting up chat-with-repo...")
    
    # Install Python dependencies
    print("\n1. Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("Failed to install dependencies")
        return
    
    # Set up tree-sitter
    print("\n2. Setting up tree-sitter...")
    if not setup_tree_sitter():
        print("\nFailed to set up tree-sitter. Please check the error messages above.")
        return
    
    print("\nSetup complete! You can now use chat-with-repo.")
    print("\nTo test the installation, try running:")
    print("python run.py")

if __name__ == "__main__":
    main() 