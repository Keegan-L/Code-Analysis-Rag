import re
import os
from collections import Counter
from .rag_processor import RAGProcessor
from typing import Dict, Any

# Initialize RAG processor
rag_processor = RAGProcessor()

def process_query(query: str, files_data: Dict[str, Dict], rag_processor: RAGProcessor) -> Dict[str, Any]:
    """Process a user query using RAG and return a response"""
    try:
        # Ensure RAG processor is initialized
        if not rag_processor.vector_index:
            rag_processor.process_repository(files_data)
        
        # Use RAG to answer the question
        response = rag_processor.answer_question(query, files_data)
        
        return {
            'answer': response['answer'],
            'sources': response.get('sources', []),
            'confidence': response.get('confidence', 1.0)
        }
    except Exception as e:
        return {
            'answer': f"Error processing query: {str(e)}",
            'sources': [],
            'confidence': 0.0
        }

def classify_query(query):
    """
    Classify the type of query and extract context
    
    Args:
        query (str): User's query
        
    Returns:
        tuple: (query_type, context)
    """
    # File-specific queries
    file_match = re.search(r'(file|in|about)\s+[\'"]?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)[\'"]?', query)
    if file_match:
        return 'file_specific', file_match.group(2)
    
    # Function-specific queries
    function_match = re.search(r'(function|method)\s+[\'"]?([a-zA-Z0-9_]+)[\'"]?', query)
    if function_match:
        return 'function', function_match.group(2)
    
    # Class-specific queries
    class_match = re.search(r'(class)\s+[\'"]?([a-zA-Z0-9_]+)[\'"]?', query)
    if class_match:
        return 'class', class_match.group(2)
    
    # Import/library-specific queries
    import_match = re.search(r'(import|library|module|package)\s+[\'"]?([a-zA-Z0-9_\-.]+)[\'"]?', query)
    if import_match:
        return 'import', import_match.group(2)
    
    # Summary queries
    if any(word in query for word in ['summarize', 'summary', 'overview', 'explain', 'structure']):
        return 'summary', None
    
    # Default to general query
    return 'general', None

def handle_file_query(query, file_path, file_info, analysis):
    """Handle a query about a specific file"""
    content = file_info['content']
    file_summary = analysis['file_summaries'].get(file_path, {})
    language = file_summary.get('language', 'Unknown')
    
    # Get detailed file information
    functions = analysis['functions'].get(file_path, [])
    classes = analysis['classes'].get(file_path, [])
    imports = analysis['imports'].get(file_path, [])
    
    # Check what kind of information is being asked for
    if 'function' in query or 'method' in query:
        # Detailed function information
        answer = f"File '{file_path}' contains {len(functions)} functions/methods:\n\n"
        for func in functions:
            answer += f"- {func['name']}:\n"
            if func['docstring']:
                answer += f"  {func['docstring'].strip()}\n"
            answer += f"  Args: {', '.join(func['args'])}\n"
            if func['returns']:
                answer += f"  Returns: {func['returns']}\n"
            answer += f"  Complexity: {func['complexity']}\n\n"
        
        return {
            'answer': answer,
            'code_references': [
                {
                    'file': file_path,
                    'description': f"Functions in {file_path}",
                    'code': extract_functions(content, functions),
                    'highlight_lines': []
                }
            ]
        }
    
    elif 'class' in query:
        # Detailed class information
        answer = f"File '{file_path}' contains {len(classes)} classes:\n\n"
        for cls in classes:
            answer += f"- {cls['name']}:\n"
            if cls['docstring']:
                answer += f"  {cls['docstring'].strip()}\n"
            if cls['inheritance']:
                answer += f"  Inherits from: {', '.join(cls['inheritance'])}\n"
            answer += f"  Methods: {', '.join(m['name'] for m in cls['methods'])}\n\n"
        
        return {
            'answer': answer,
            'code_references': [
                {
                    'file': file_path,
                    'description': f"Classes in {file_path}",
                    'code': extract_classes(content, classes),
                    'highlight_lines': []
                }
            ]
        }
    
    elif 'import' in query:
        # Detailed import information
        answer = f"File '{file_path}' imports the following:\n\n"
        for imp in imports:
            if imp['type'] == 'import':
                answer += f"- import {imp['name']}"
                if imp['alias']:
                    answer += f" as {imp['alias']}"
            else:
                answer += f"- from {imp['module']} import {imp['name']}"
                if imp['alias']:
                    answer += f" as {imp['alias']}"
            answer += f" (line {imp['line_number']})\n"
        
        return {
            'answer': answer,
            'code_references': [
                {
                    'file': file_path,
                    'description': f"Imports in {file_path}",
                    'code': extract_imports(content),
                    'highlight_lines': []
                }
            ]
        }
    
    else:
        # General file summary
        answer = f"File '{file_path}' is a {language} file with {file_summary.get('total_lines', 0)} lines of code.\n\n"
        
        # Add file purpose if available
        if file_summary.get('purpose'):
            answer += f"Purpose: {file_summary['purpose']}\n\n"
        
        # Add key statistics
        answer += f"Statistics:\n"
        answer += f"- Functions: {len(functions)}\n"
        answer += f"- Classes: {len(classes)}\n"
        answer += f"- Imports: {len(imports)}\n"
        
        # Add main components
        if functions or classes:
            answer += "\nMain Components:\n"
            for func in functions[:3]:  # Show top 3 functions
                answer += f"- Function: {func['name']}\n"
                if func['docstring']:
                    answer += f"  {func['docstring'].strip()}\n"
            
            for cls in classes[:3]:  # Show top 3 classes
                answer += f"- Class: {cls['name']}\n"
                if cls['docstring']:
                    answer += f"  {cls['docstring'].strip()}\n"
        
        return {
            'answer': answer,
            'code_references': [
                {
                    'file': file_path,
                    'description': f"Overview of {file_path}",
                    'code': truncate_code(content, max_lines=30),
                    'highlight_lines': []
                }
            ]
        }

def handle_summary_query(query, files_data, analysis):
    """Handle a summary/overview query about the repository"""
    # Get repository summary
    repo_summary = analysis['summary']
    
    # If specific language is mentioned, focus on those files
    language_match = re.search(r'(python|javascript|typescript|html|css|java|c\+\+|ruby|go|rust)', query, re.IGNORECASE)
    if language_match:
        language = language_match.group(1).capitalize()
        if language.lower() == 'javascript':
            language = 'JavaScript'
        elif language.lower() == 'typescript':
            language = 'TypeScript'
        elif language.lower() == 'c++':
            language = 'C++'
        
        # Filter files by language
        language_files = {
            path: data for path, data in files_data.items() 
            if analysis['file_summaries'].get(path, {}).get('language', '') == language
        }
        
        if not language_files:
            return {
                'answer': f"No {language} files found in the repository.",
                'code_references': []
            }
        
        # Generate language-specific summary
        language_summary = f"Found {len(language_files)} {language} files in the repository."
        
        # Get a sample of these files to show
        sample_files = list(language_files.items())[:3]
        code_references = [
            {
                'file': path,
                'description': f"Sample {language} file",
                'code': truncate_code(data['content'], max_lines=15),
                'highlight_lines': []
            }
            for path, data in sample_files
        ]
        
        return {
            'answer': language_summary,
            'code_references': code_references
        }
    
    # If "structure" is mentioned, focus on directory structure
    elif 'structure' in query:
        # Build directory tree
        dirs = set()
        for path in files_data.keys():
            parts = path.split('/')
            for i in range(1, len(parts)):
                dirs.add('/'.join(parts[:i]))
        
        dir_tree = "Repository structure:\n"
        for path in sorted(list(dirs) + list(files_data.keys())):
            depth = path.count('/')
            dir_tree += f"{'  ' * depth}{'└─ ' if '/' in path else ''}{os.path.basename(path)}\n"
        
        return {
            'answer': "Here's the overall structure of the repository:",
            'code_references': [
                {
                    'file': 'Directory Structure',
                    'description': "Repository file organization",
                    'code': dir_tree,
                    'highlight_lines': []
                }
            ]
        }
    
    # Default repository summary
    else:
        # Get most important files (largest, most functions, etc.)
        important_files = identify_important_files(files_data, analysis)
        
        code_references = [
            {
                'file': path,
                'description': reason,
                'code': truncate_code(files_data[path]['content'], max_lines=15),
                'highlight_lines': []
            }
            for path, reason in important_files[:3]
        ]
        
        return {
            'answer': repo_summary,
            'code_references': code_references
        }

def handle_function_query(query, function_name, files_data, analysis):
    """Handle a query about a specific function"""
    # Find all occurrences of the function
    function_occurrences = []
    
    for file_path, functions in analysis['functions'].items():
        for func in functions:
            if function_name.lower() in func['name'].lower():
                function_occurrences.append((file_path, func))
    
    if not function_occurrences:
        return {
            'answer': f"No function named '{function_name}' found in the repository.",
            'code_references': []
        }
    
    # Create response
    answer = f"Found {len(function_occurrences)} occurrences of function '{function_name}'."
    
    code_references = []
    for file_path, func in function_occurrences[:3]:  # Limit to top 3
        # Extract function code
        line_number = func['line_number']
        code = extract_function_code(files_data[file_path]['content'], func['name'], line_number)
        
        code_references.append({
            'file': file_path,
            'description': f"Function {func['name']} (line {line_number})",
            'code': code,
            'highlight_lines': []
        })
    
    return {
        'answer': answer,
        'code_references': code_references
    }

def handle_class_query(query, class_name, files_data, analysis):
    """Handle a query about a specific class"""
    # Find all occurrences of the class
    class_occurrences = []
    
    for file_path, classes in analysis['classes'].items():
        for cls in classes:
            if class_name.lower() in cls['name'].lower():
                class_occurrences.append((file_path, cls))
    
    if not class_occurrences:
        return {
            'answer': f"No class named '{class_name}' found in the repository.",
            'code_references': []
        }
    
    # Create response
    answer = f"Found {len(class_occurrences)} occurrences of class '{class_name}'."
    
    code_references = []
    for file_path, cls in class_occurrences[:3]:  # Limit to top 3
        # Extract class code
        line_number = cls['line_number']
        code = extract_class_code(files_data[file_path]['content'], cls['name'], line_number)
        
        code_references.append({
            'file': file_path,
            'description': f"Class {cls['name']} (line {line_number})",
            'code': code,
            'highlight_lines': []
        })
    
    return {
        'answer': answer,
        'code_references': code_references
    }

def handle_import_query(query, library_name, files_data, analysis):
    """Handle a query about library usage across the repository"""
    # Find all files that use the library
    library_files = []
    library_usage = {
        'imports': [],
        'functions': [],
        'classes': [],
        'total_usage': 0
    }
    
    # Search through all files
    for file_path, file_info in files_data.items():
        content = file_info['content']
        imports = analysis['imports'].get(file_path, [])
        
        # Check if library is imported in this file
        file_imports = []
        for imp in imports:
            if library_name.lower() in imp['name'].lower() or library_name.lower() in imp.get('module', '').lower():
                file_imports.append(imp)
                library_usage['imports'].append({
                    'file': file_path,
                    'import': imp,
                    'line_number': imp['line_number']
                })
        
        if file_imports:
            library_files.append(file_path)
            
            # Find functions that use the library
            functions = analysis['functions'].get(file_path, [])
            for func in functions:
                if library_name.lower() in func['docstring'].lower():
                    library_usage['functions'].append({
                        'file': file_path,
                        'function': func['name'],
                        'line_number': func['line_number']
                    })
            
            # Find classes that use the library
            classes = analysis['classes'].get(file_path, [])
            for cls in classes:
                if library_name.lower() in cls['docstring'].lower():
                    library_usage['classes'].append({
                        'file': file_path,
                        'class': cls['name'],
                        'line_number': cls['line_number']
                    })
    
    # Calculate total usage
    library_usage['total_usage'] = len(library_usage['imports']) + len(library_usage['functions']) + len(library_usage['classes'])
    
    if not library_files:
        return {
            'answer': f"The library '{library_name}' is not used in this repository.",
            'code_references': []
        }
    
    # Generate detailed response
    answer = f"The library '{library_name}' is used in {len(library_files)} files:\n\n"
    
    # Add import details
    answer += f"Total imports: {len(library_usage['imports'])}\n"
    answer += f"Functions using the library: {len(library_usage['functions'])}\n"
    answer += f"Classes using the library: {len(library_usage['classes'])}\n"
    
    # Prepare code references
    code_references = []
    
    # Add sample imports
    if library_usage['imports']:
        sample_import = library_usage['imports'][0]
        file_path = sample_import['file']
        content = files_data[file_path]['content']
        lines = content.split('\n')
        start_line = max(0, sample_import['line_number'] - 2)
        end_line = min(len(lines), sample_import['line_number'] + 2)
        
        code_references.append({
            'file': file_path,
            'description': f"Import of {library_name}",
            'code': '\n'.join(lines[start_line:end_line]),
            'highlight_lines': [sample_import['line_number'] - start_line]
        })
    
    # Add sample function usage
    if library_usage['functions']:
        sample_func = library_usage['functions'][0]
        file_path = sample_func['file']
        content = files_data[file_path]['content']
        func_code = extract_function_code(content, sample_func['function'], sample_func['line_number'])
        
        code_references.append({
            'file': file_path,
            'description': f"Function using {library_name}",
            'code': func_code,
            'highlight_lines': []
        })
    
    # Add sample class usage
    if library_usage['classes']:
        sample_class = library_usage['classes'][0]
        file_path = sample_class['file']
        content = files_data[file_path]['content']
        class_code = extract_class_code(content, sample_class['class'], sample_class['line_number'])
        
        code_references.append({
            'file': file_path,
            'description': f"Class using {library_name}",
            'code': class_code,
            'highlight_lines': []
        })
    
    return {
        'answer': answer,
        'code_references': code_references,
        'library_usage': library_usage
    }

def handle_general_query(query, files_data, analysis):
    """
    Handle general queries about the repository
    
    Args:
        query (str): User's query
        files_data (dict): Dictionary of file paths and their contents
        analysis (dict): Repository analysis results
        
    Returns:
        dict: Response containing answer and relevant code references
    """
    # Get repository summary
    repo_summary = analysis['summary']
    
    # Find relevant code snippets based on query keywords
    keywords = extract_keywords(query)
    relevant_files = find_relevant_files(files_data, keywords)
    
    # Prepare code references
    code_references = []
    for file_path, relevance_score in relevant_files[:3]:  # Limit to top 3 most relevant
        content = files_data[file_path]['content']
        code_references.append({
            'file': file_path,
            'description': f"Relevant code from {file_path}",
            'code': truncate_code(content, max_lines=20),
            'highlight_lines': []
        })
    
    return {
        'answer': repo_summary,
        'code_references': code_references
    }

def find_relevant_files(files_data, keywords):
    """
    Find files most relevant to the query keywords
    
    Args:
        files_data (dict): Dictionary of file paths and their contents
        keywords (list): List of keywords from the query
        
    Returns:
        list: List of (file_path, relevance_score) tuples
    """
    file_scores = []
    
    for file_path, file_info in files_data.items():
        content = file_info['content'].lower()
        score = sum(1 for keyword in keywords if keyword.lower() in content)
        if score > 0:
            file_scores.append((file_path, score))
    
    # Sort by relevance score
    return sorted(file_scores, key=lambda x: x[1], reverse=True)

def extract_keywords(query):
    """
    Extract important keywords from the query
    
    Args:
        query (str): User's query
        
    Returns:
        list: List of keywords
    """
    # Remove common words and split into keywords
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = re.findall(r'\w+', query.lower())
    return [word for word in words if word not in common_words]

def truncate_code(content, max_lines=30):
    """
    Truncate code to a maximum number of lines
    
    Args:
        content (str): Code content
        max_lines (int): Maximum number of lines to show
        
    Returns:
        str: Truncated code with ellipsis
    """
    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content
    
    first_part = '\n'.join(lines[:max_lines//2])
    last_part = '\n'.join(lines[-max_lines//2:])
    return f"{first_part}\n...\n{last_part}"

def identify_important_files(files_data, analysis):
    """Identify the most important files in the repository"""
    file_importance = []
    
    for file_path, file_info in files_data.items():
        # Get the file summary
        file_summary = analysis['file_summaries'].get(file_path, {})
        
        # Calculate importance score based on:
        # 1. Size of the file
        # 2. Number of functions and classes
        # 3. Number of imports (indicates dependencies)
        size_score = file_summary.get('code_lines', 0) / 100  # Normalize size
        functions_score = len(analysis['functions'].get(file_path, [])) * 2
        classes_score = len(analysis['classes'].get(file_path, [])) * 3
        imports_score = len(analysis['imports'].get(file_path, [])) * 1.5
        
        importance_score = size_score + functions_score + classes_score + imports_score
        
        # Add a reason for importance
        reason = "Important file"
        if functions_score > classes_score and functions_score > size_score:
            reason = f"Contains {len(analysis['functions'].get(file_path, []))} functions"
        elif classes_score > functions_score and classes_score > size_score:
            reason = f"Contains {len(analysis['classes'].get(file_path, []))} classes"
        elif 'main' in file_path.lower() or 'app' in file_path.lower():
            reason = "Main application file"
        elif file_path.endswith('__init__.py'):
            reason = "Module initialization file"
        elif imports_score > functions_score and imports_score > classes_score:
            reason = "Key dependency hub"
        
        file_importance.append((file_path, reason, importance_score))
    
    # Sort by importance score
    sorted_files = sorted(file_importance, key=lambda x: x[2], reverse=True)
    
    # Return just the path and reason
    return [(path, reason) for path, reason, score in sorted_files]

def extract_imports(content):
    """Extract import statements from code"""
    lines = content.split('\n')
    import_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('import ') or line.startswith('from ') or 'require(' in line:
            # Add a few lines of context if available
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            import_lines.extend(lines[start:end])
            import_lines.append('')  # Add a blank line between import groups
    
    return '\n'.join(import_lines).strip()

def extract_functions(content, functions_info):
    """Extract function definitions from code"""
    if not functions_info:
        return "No functions found"
    
    lines = content.split('\n')
    function_snippets = []
    
    for func in functions_info:
        line_number = func['line_number'] - 1  # 0-indexed
        
        # Simple approach: get a chunk of lines around the function
        start = max(0, line_number - 1)
        
        # Try to detect the end of the function (indentation-based)
        end = start + 1
        while end < len(lines) and (end == start or lines[end].startswith(' ') or lines[end].startswith('\t') or not lines[end].strip()):
            end += 1
        
        # If we can't detect the end well, just take a reasonable chunk
        if end - start < 3:
            end = min(len(lines), start + 15)
        
        function_snippet = '\n'.join(lines[start:end])
        function_snippets.append(function_snippet)
    
    return '\n\n'.join(function_snippets)

def extract_classes(content, classes_info):
    """Extract class definitions from code"""
    if not classes_info:
        return "No classes found"
    
    lines = content.split('\n')
    class_snippets = []
    
    for cls in classes_info:
        line_number = cls['line_number'] - 1  # 0-indexed
        
        # Simple approach: get a chunk of lines around the class
        start = max(0, line_number - 1)
        
        # Try to detect the end of the class (indentation-based)
        # This is a very simple approach and might not work for complex classes
        end = start + 1
        while end < len(lines) and (end == start or lines[end].startswith(' ') or lines[end].startswith('\t') or not lines[end].strip()):
            end += 1
        
        # If we can't detect the end well, just take a reasonable chunk
        if end - start < 5:
            end = min(len(lines), start + 20)
        
        class_snippet = '\n'.join(lines[start:end])
        class_snippets.append(class_snippet)
    
    return '\n\n'.join(class_snippets)

def extract_function_code(content, function_name, line_number):
    """Extract the full code of a function"""
    lines = content.split('\n')
    start = max(0, line_number - 1)  # 0-indexed
    
    # Find the end of the function (based on indentation)
    def_line = lines[start]
    indent_level = len(def_line) - len(def_line.lstrip())
    
    end = start + 1
    while end < len(lines):
        if lines[end].strip() and not lines[end].startswith(' ' * (indent_level + 1)) and not lines[end].startswith('\t' * (indent_level // 4 + 1)):
            break
        end += 1
    
    return '\n'.join(lines[start:end])

def extract_class_code(content, class_name, line_number):
    """Extract the full code of a class"""
    lines = content.split('\n')
    start = max(0, line_number - 1)  # 0-indexed
    
    # Find the end of the class (based on indentation)
    class_line = lines[start]
    indent_level = len(class_line) - len(class_line.lstrip())
    
    end = start + 1
    while end < len(lines):
        if lines[end].strip() and not lines[end].startswith(' ' * (indent_level + 1)) and not lines[end].startswith('\t' * (indent_level // 4 + 1)):
            break
        end += 1
    
    return '\n'.join(lines[start:end])

def split_code_into_chunks(content, chunk_size=20):
    """Split code content into chunks for analysis"""
    lines = content.split('\n')
    chunks = []
    
    for i in range(0, len(lines), chunk_size):
        chunk = '\n'.join(lines[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks