import os
import re
import ast
from collections import defaultdict
from typing import Dict, List, Any

def analyze_repository(files_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the repository structure and code content
    
    Args:
        files_data (dict): Dictionary of file paths and their contents
        
    Returns:
        dict: Analysis results containing summary, imports, functions, classes, etc.
    """
    # Initialize analysis results
    analysis = {
        'languages': {},
        'imports': defaultdict(list),
        'functions': defaultdict(list),
        'classes': defaultdict(list),
        'file_summaries': {},
        'dependencies': defaultdict(set),
        'total_lines': 0,
        'files_count': len(files_data),
        'documentation': {},
        'code_relationships': defaultdict(list),
        'entry_points': [],
        'main_components': [],
        'files_data': files_data
    }
    
    # Process each file
    for file_path, file_info in files_data.items():
        content = file_info['content']
        extension = file_info['extension']
        
        # Increment line count
        lines = content.split('\n')
        analysis['total_lines'] += len(lines)
        
        # Track language statistics
        language = get_file_language(file_path)
        analysis['languages'][language] = analysis['languages'].get(language, 0) + 1
        
        # Analyze file based on language
        if language == 'Python':
            analyze_python_file(file_path, content, analysis)
        elif language in ['JavaScript', 'TypeScript', 'React/JSX', 'React/TSX']:
            analyze_js_file(file_path, content, analysis)
        
        # Generate file summary and documentation
        analysis['file_summaries'][file_path] = generate_file_summary(file_path, content, language)
        analysis['documentation'][file_path] = generate_file_documentation(file_path, content, language)
    
    # Analyze code relationships and identify main components
    analyze_code_relationships(analysis)
    
    # Generate overall repository summary and documentation
    analysis['summary'] = generate_repository_summary(analysis)
    analysis['repository_documentation'] = generate_repository_documentation(analysis)
    
    return analysis

def analyze_python_file(file_path: str, content: str, analysis: Dict[str, Any]) -> None:
    """Analyze a Python file for imports, functions, and classes"""
    try:
        tree = ast.parse(content)
        
        # Find imports and track dependencies
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    module_name = name.name.split('.')[0]
                    analysis['dependencies'][file_path].add(module_name)
                    analysis['imports'][file_path].append({
                        'type': 'import',
                        'name': name.name,
                        'alias': name.asname,
                        'line_number': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ''
                for name in node.names:
                    analysis['dependencies'][file_path].add(module)
                    analysis['imports'][file_path].append({
                        'type': 'from',
                        'module': module,
                        'name': name.name,
                        'alias': name.asname,
                        'line_number': node.lineno
                    })
            
            # Find functions with detailed analysis
            elif isinstance(node, ast.FunctionDef):
                function_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'defaults': [ast.unparse(default) for default in node.args.defaults],
                    'docstring': ast.get_docstring(node) or '',
                    'decorators': [ast.unparse(decorator) for decorator in node.decorator_list],
                    'returns': ast.unparse(node.returns) if node.returns else None,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'complexity': calculate_function_complexity(node)
                }
                analysis['functions'][file_path].append(function_info)
                
                # Track function relationships
                for call in ast.walk(node):
                    if isinstance(call, ast.Call):
                        if isinstance(call.func, ast.Name):
                            analysis['code_relationships'][f"{file_path}:{node.name}"].append({
                                'type': 'calls',
                                'target': call.func.id,
                                'line': call.lineno
                            })
                
            # Find classes with detailed analysis
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'bases': [get_name(base) for base in node.bases],
                    'methods': [],
                    'docstring': ast.get_docstring(node) or '',
                    'decorators': [ast.unparse(decorator) for decorator in node.decorator_list],
                    'inheritance': [get_name(base) for base in node.bases]
                }
                
                # Get class methods with detailed analysis
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            'name': item.name,
                            'line_number': item.lineno,
                            'args': [arg.arg for arg in item.args.args],
                            'defaults': [ast.unparse(default) for default in item.args.defaults],
                            'docstring': ast.get_docstring(item) or '',
                            'decorators': [ast.unparse(decorator) for decorator in item.decorator_list],
                            'returns': ast.unparse(item.returns) if item.returns else None,
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                            'complexity': calculate_function_complexity(item)
                        }
                        class_info['methods'].append(method_info)
                
                analysis['classes'][file_path].append(class_info)
                
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error analyzing {file_path}: {str(e)}")

def calculate_function_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity of a function"""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.BoolOp)):
            complexity += 1
    return complexity

def generate_file_documentation(file_path: str, content: str, language: str) -> Dict[str, Any]:
    """Generate detailed documentation for a file"""
    doc = {
        'overview': '',
        'components': [],
        'usage': '',
        'dependencies': [],
        'examples': []
    }
    
    if language == 'Python':
        try:
            tree = ast.parse(content)
            module_doc = ast.get_docstring(tree)
            if module_doc:
                doc['overview'] = module_doc
            
            # Extract examples from docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    docstring = ast.get_docstring(node)
                    if docstring and 'Example:' in docstring:
                        example = docstring.split('Example:')[1].strip()
                        doc['examples'].append({
                            'component': node.name,
                            'example': example
                        })
        except:
            pass
    
    return doc

def generate_repository_documentation(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive repository documentation"""
    doc = {
        'overview': '',
        'architecture': '',
        'components': [],
        'entry_points': [],
        'dependencies': {},
        'usage_guide': ''
    }
    
    # Generate overview
    main_language = max(analysis['languages'].items(), key=lambda x: x[1])[0]
    doc['overview'] = f"""
This is a {main_language} repository containing {analysis['files_count']} files.
The codebase is organized into several key components and follows modern development practices.
"""
    
    # Document main components
    for file_path, classes in analysis['classes'].items():
        for class_info in classes:
            doc['components'].append({
                'name': class_info['name'],
                'file': file_path,
                'description': class_info['docstring'],
                'methods': [m['name'] for m in class_info['methods']]
            })
    
    # Document dependencies
    for file_path, deps in analysis['dependencies'].items():
        doc['dependencies'][file_path] = list(deps)
    
    # Generate usage guide
    doc['usage_guide'] = generate_usage_guide(analysis)
    
    return doc

def generate_usage_guide(analysis: Dict[str, Any]) -> str:
    """Generate a usage guide for the repository"""
    guide = []
    
    # Add overview
    guide.append("## Usage Guide")
    guide.append("\nThis guide explains how to use the main components of the repository.")
    
    # Document main classes and their usage
    for file_path, classes in analysis['classes'].items():
        for class_info in classes:
            guide.append(f"\n### {class_info['name']}")
            guide.append(f"\nLocation: {file_path}")
            if class_info['docstring']:
                guide.append(f"\n{class_info['docstring']}")
            
            if class_info['methods']:
                guide.append("\n#### Methods:")
                for method in class_info['methods']:
                    guide.append(f"\n- {method['name']}: {method['docstring'] or 'No documentation available'}")
    
    return "\n".join(guide)

def analyze_code_relationships(analysis: Dict[str, Any]) -> None:
    """Analyze relationships between code components"""
    # Identify entry points (files that are imported but don't import much)
    for file_path, imports in analysis['imports'].items():
        if len(imports) < 3:  # Simple heuristic for entry points
            analysis['entry_points'].append(file_path)
    
    # Identify main components (files with many imports or exports)
    for file_path in analysis['files_data'].keys():  # Use keys() instead of direct iteration
        import_count = len(analysis['imports'][file_path])
        export_count = sum(1 for other_file, other_imports in analysis['imports'].items() 
                         if any(imp['name'].startswith(file_path.split('/')[-1].split('.')[0]) 
                              for imp in other_imports))
        
        if import_count + export_count > 5:  # Another simple heuristic
            analysis['main_components'].append(file_path)

def generate_repository_summary(analysis: Dict[str, Any]) -> str:
    """Generate a comprehensive summary of the repository"""
    summary = []
    
    # Basic repository information
    main_language = max(analysis['languages'].items(), key=lambda x: x[1])[0]
    summary.append(f"This is a {main_language} repository containing {analysis['files_count']} files with a total of {analysis['total_lines']} lines of code.")
    
    # Language breakdown
    if len(analysis['languages']) > 1:
        summary.append("\nLanguage Distribution:")
        for lang, count in analysis['languages'].items():
            summary.append(f"- {lang}: {count} files")
    
    # Main components and their purposes
    summary.append("\nMain Components:")
    for file_path, classes in analysis['classes'].items():
        for class_info in classes:
            if class_info['docstring']:
                summary.append(f"\n- {class_info['name']} (in {file_path}):")
                summary.append(f"  {class_info['docstring'].strip()}")
                if class_info['methods']:
                    summary.append("  Key methods:")
                    for method in class_info['methods'][:3]:  # Show top 3 methods
                        if method['docstring']:
                            summary.append(f"  - {method['name']}: {method['docstring'].strip()}")
    
    # Key dependencies
    all_deps = set()
    for deps in analysis['dependencies'].values():
        all_deps.update(deps)
    
    if all_deps:
        summary.append("\nKey Dependencies:")
        for dep in sorted(all_deps)[:5]:  # Show top 5 dependencies
            summary.append(f"- {dep}")
    
    # Entry points
    if analysis['entry_points']:
        summary.append("\nEntry Points:")
        for entry in analysis['entry_points']:
            summary.append(f"- {entry}")
    
    # Code relationships
    if analysis['code_relationships']:
        summary.append("\nKey Code Relationships:")
        for component, relationships in list(analysis['code_relationships'].items())[:3]:  # Show top 3 relationships
            file, name = component.split(':')
            summary.append(f"\n{name} (in {file}):")
            for rel in relationships[:3]:  # Show top 3 relationships per component
                summary.append(f"- {rel['type']} {rel['target']} at line {rel['line']}")
    
    return '\n'.join(summary)

def get_file_language(file_path: str) -> str:
    """Determine the programming language of a file based on its extension"""
    extension = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React/JSX',
        '.tsx': 'React/TSX',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.md': 'Markdown',
        '.txt': 'Text'
    }
    return language_map.get(extension, 'Unknown')

def analyze_js_file(file_path, content, analysis):
    """Analyze a JavaScript file for imports, functions, and classes"""
    # Find imports (ES6 style)
    import_pattern = r'import\s+(?:{[^}]*}|[^{][^;]*?)\s+from\s+[\'"]([^\'"]+)[\'"]'
    require_pattern = r'(?:const|let|var)\s+([^=]+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'
    
    imports = []
    
    # Find ES6 imports
    for match in re.finditer(import_pattern, content):
        imports.append({
            'type': 'import',
            'source': match.group(1),
            'statement': match.group(0).strip()
        })
    
    # Find CommonJS require
    for match in re.finditer(require_pattern, content):
        imports.append({
            'type': 'require',
            'variable': match.group(1).strip(),
            'source': match.group(2),
            'statement': match.group(0).strip()
        })
    
    analysis['imports'][file_path] = imports
    
    # Find functions
    function_pattern = r'(?:function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)|(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:function|\([^)]*\)\s*=>))'
    
    functions = []
    for match in re.finditer(function_pattern, content):
        func_name = match.group(1) if match.group(1) else match.group(3)
        if func_name:
            functions.append({
                'name': func_name,
                'line_number': content[:match.start()].count('\n') + 1,
            })
    
    analysis['functions'][file_path] = functions
    
    # Find classes (ES6)
    class_pattern = r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*))?\s*{'
    
    classes = []
    for match in re.finditer(class_pattern, content):
        class_name = match.group(1)
        parent_class = match.group(2)
        
        # Simple approach to find methods (not comprehensive)
        class_content = extract_balanced_braces(content[match.start():])
        method_pattern = r'(?:async\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*{'
        
        methods = []
        for method_match in re.finditer(method_pattern, class_content):
            method_name = method_match.group(1)
            if method_name and method_name not in ('constructor', 'if', 'for', 'while', 'switch'):
                methods.append({
                    'name': method_name,
                    'line_number': content[:match.start() + method_match.start()].count('\n') + 1,
                })
        
        classes.append({
            'name': class_name,
            'line_number': content[:match.start()].count('\n') + 1,
            'parent': parent_class,
            'methods': methods
        })
    
    analysis['classes'][file_path] = classes

def extract_balanced_braces(text):
    """Extract content between balanced braces"""
    stack = []
    start = text.find('{')
    if start == -1:
        return ''
    
    for i, char in enumerate(text[start:], start):
        if char == '{':
            stack.append('{')
        elif char == '}':
            stack.pop()
            if not stack:
                return text[start:i+1]
    
    return text[start:]  # In case of unbalanced braces

def get_name(node):
    """Helper to get name from AST node"""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{get_name(node.value)}.{node.attr}"
    return str(node)

def generate_file_summary(file_path, content, language):
    """Generate a summary for a single file"""
    lines = content.split('\n')
    code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
    
    summary = {
        'path': file_path,
        'language': language,
        'total_lines': len(lines),
        'code_lines': len(code_lines),
        'size_bytes': len(content),
    }
    
    return summary