import os
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import uuid
import zipfile
import markdown

from utils.file_processor import extract_repository
from utils.query_processor import process_query
from utils.code_analyzer import analyze_repository, generate_repository_documentation
from utils.rag_processor import RAGProcessor

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size

# Store repository data in memory (for this demo)
repositories = {}

# Initialize RAG processor
rag_processor = RAGProcessor()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_repository():
    """Handle repository upload"""
    try:
        if 'repository' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['repository']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.zip'):
            return jsonify({'error': 'Please upload a zip file'}), 400
        
        # Generate a unique ID for this repository
        repo_id = str(uuid.uuid4())
        session['repo_id'] = repo_id
        
        # Save the file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Verify it's a valid zip file
        try:
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                # Check if the zip file is not empty
                if not zip_ref.namelist():
                    raise ValueError("The zip file is empty")
        except zipfile.BadZipFile:
            os.remove(filepath)
            return jsonify({'error': 'Invalid zip file format'}), 400
        
        # Process the repository
        try:
            files_data = extract_repository(filepath)
            if not files_data:
                raise ValueError("No files could be extracted from the zip")
            
            analysis = analyze_repository(files_data)
            
            # Store repository data for later use
            repositories[repo_id] = {
                'files': files_data,
                'analysis': analysis
            }
            
            # Generate repository summary using RAG
            if not rag_processor.vector_index:
                rag_processor.process_repository(files_data)
            
            # Ask the RAG system to generate a summary
            summary_response = rag_processor.answer_question(
                "What does this codebase do? Please provide a comprehensive summary explaining its purpose, main components, and how they work together.",
                files_data
            )
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'message': 'Repository uploaded and processed successfully',
                'repo_id': repo_id,
                'files': list(files_data.keys()),
                'summary': summary_response['answer']
            })
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error processing repository: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/query', methods=['POST'])
def handle_query():
    """Process a user query about the repository"""
    try:
        data = request.get_json()
        if not data or 'query' not in data or 'repo_id' not in data:
            return jsonify({'error': 'Missing query or repo_id'}), 400
        
        repo_id = data['repo_id']
        if repo_id not in repositories:
            return jsonify({'error': 'Repository not found'}), 404
        
        # Get repository data
        repo_data = repositories[repo_id]
        files_data = repo_data['files']
        
        # Process the query
        response = process_query(data['query'], files_data, rag_processor)
        
        return jsonify({
            'answer': response['answer'],
            'sources': response['sources'],
            'confidence': response['confidence']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-docs', methods=['POST'])
def generate_documentation():
    """Generate documentation for the repository and return a zip file with documented code"""
    try:
        print("\n=== Starting Documentation Generation ===")
        print("Request headers:", dict(request.headers))
        print("Request method:", request.method)
        
        data = request.get_json()
        print("Request data:", data)
        
        if not data or 'repo_id' not in data:
            print("Error: Missing repo_id in request")
            return jsonify({'error': 'Missing repo_id'}), 400
        
        repo_id = data['repo_id']
        print("Processing repo_id:", repo_id)
        print("Available repositories:", list(repositories.keys()))
        
        if repo_id not in repositories:
            print("Error: Repository not found")
            return jsonify({'error': 'Repository not found'}), 404
        
        # Get repository data
        repo_data = repositories[repo_id]
        files_data = repo_data['files']
        print(f"Processing {len(files_data)} files")
        print("File paths:", list(files_data.keys()))
        
        # Create a temporary directory for the documented files
        temp_dir = tempfile.mkdtemp()
        print("Created temp directory:", temp_dir)
        
        try:
            # Process each file
            for file_path, file_info in files_data.items():
                print(f"\nProcessing file: {file_path}")
                # Get the file content
                content = file_info['content']
                
                # Generate documentation for this file
                print("Generating documentation...")
                file_docs = generate_file_documentation(file_path, content)
                print("Documentation generated")
                
                # Create the documented content
                documented_content = f"""'''
{file_docs}
'''

{content}"""
                
                # Create the file in the temp directory
                file_dir = os.path.dirname(os.path.join(temp_dir, file_path))
                os.makedirs(file_dir, exist_ok=True)
                
                with open(os.path.join(temp_dir, file_path), 'w', encoding='utf-8') as f:
                    f.write(documented_content)
                print(f"File written to {os.path.join(temp_dir, file_path)}")
            
            # Create a zip file
            zip_path = os.path.join(tempfile.gettempdir(), f'documented_code_{repo_id}.zip')
            print("\nCreating zip file at:", zip_path)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
                        print(f"Added to zip: {arcname}")
            
            print("Zip file created successfully")
            print("=== Documentation Generation Complete ===\n")
            
            # Send the zip file
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'documented_code.zip'
            )
            
        finally:
            # Clean up temporary files
            print("Cleaning up temporary files")
            shutil.rmtree(temp_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
    except Exception as e:
        print("Error in documentation generation:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def generate_file_documentation(file_path: str, content: str) -> str:
    """Generate documentation for a single file"""
    try:
        # Use RAG to generate documentation
        if not rag_processor.vector_index:
            rag_processor.process_repository({file_path: {'content': content}})
        
        # Ask specific questions about the file
        questions = [
            "What is the purpose of this file?",
            "What are the main functions or classes in this file?",
            "How does this file interact with other parts of the codebase?"
        ]
        
        docs = []
        for question in questions:
            response = rag_processor.answer_question(question, {file_path: {'content': content}})
            docs.append(f"{question}\n{response['answer']}\n")
        
        return "\n".join(docs)
    except Exception as e:
        return f"Error generating documentation: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)