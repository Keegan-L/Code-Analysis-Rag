import os
import zipfile
import tempfile
import shutil
from pathlib import Path

def extract_repository(zip_path):
    """
    Extract and process files from a zip repository
    
    Args:
        zip_path (str): Path to the zip file
        
    Returns:
        dict: Dictionary with file paths as keys and file contents as values
    """
    # Create a temporary directory to extract files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Get all files from the extracted directory
        files_data = {}
        for root, _, files in os.walk(temp_dir):
            for file in files:
                # Get the full file path
                file_path = os.path.join(root, file)
                
                # Skip hidden files and common non-code files
                if file.startswith('.') or is_binary_file(file):
                    continue
                
                # Get the relative path from the temp directory
                rel_path = os.path.relpath(file_path, temp_dir)
                
                # Read the file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Add to our files dictionary
                    files_data[rel_path] = {
                        'content': content,
                        'extension': os.path.splitext(file)[1],
                        'size': os.path.getsize(file_path)
                    }
                except (UnicodeDecodeError, IOError):
                    # Skip files that can't be read as text
                    continue
        
        return files_data
    
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def is_binary_file(filename):
    """
    Check if a file is likely a binary file based on extension
    
    Args:
        filename (str): Filename to check
        
    Returns:
        bool: True if the file is likely binary, False otherwise
    """
    binary_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',  # Images
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',  # Documents
        '.zip', '.tar', '.gz', '.7z', '.rar',  # Archives
        '.exe', '.dll', '.so', '.dylib',  # Executables
        '.pyc', '.pyo', '.pyd',  # Python compiled
        '.class',  # Java compiled
        '.o', '.obj',  # Object files
        '.bin', '.dat',  # Binary data
    }
    
    _, ext = os.path.splitext(filename.lower())
    return ext in binary_extensions

def get_file_language(file_path):
    """
    Determine the programming language of a file based on its extension
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Name of the programming language or 'unknown'
    """
    extension_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React/JSX',
        '.tsx': 'React/TSX',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.java': 'Java',
        '.c': 'C',
        '.cpp': 'C++',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.go': 'Go',
        '.rs': 'Rust',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.sh': 'Shell',
        '.bat': 'Batch',
        '.ps1': 'PowerShell',
        '.sql': 'SQL',
        '.md': 'Markdown',
        '.json': 'JSON',
        '.xml': 'XML',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.ini': 'INI',
        '.cfg': 'Config',
        '.conf': 'Config',
    }
    
    _, ext = os.path.splitext(file_path.lower())
    return extension_map.get(ext, 'unknown')