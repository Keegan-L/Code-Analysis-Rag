Code Analysis RAG (Retrieval-Augmented Generation) System
====================================================

A powerful web application that allows users to upload code repositories and interact with them using natural language queries. The system uses advanced code analysis and RAG techniques to provide intelligent responses about the codebase.

Features
--------
1. Repository Upload and Analysis
   - Upload zip files containing code repositories
   - Automatic code analysis and indexing
   - Support for multiple programming languages
   - Detailed code structure analysis

2. Intelligent Code Analysis
   - Function and class analysis
   - Dependency tracking
   - Code relationship mapping
   - Complexity metrics
   - Documentation generation

3. Natural Language Interaction
   - Ask questions about the codebase
   - Get code explanations
   - Request documentation
   - Receive optimization suggestions

4. Documentation Generation
   - Automatic documentation for files
   - Repository overview and architecture
   - Usage guides
   - Example extraction from docstrings

Setup Instructions
-----------------
1. Install Dependencies:
   ```bash
   pip install flask werkzeug sentence-transformers faiss-cpu openai python-dotenv
   ```

2. Set up OpenAI API Key:
   Create a .env file in the project root with:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

3. Run the Application:
   ```bash
   python3 app.py
   ```

4. Access the Web Interface:
   Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

Usage Guide
-----------
1. Upload a Repository:
   - Click "Choose File" and select a zip file containing your code
   - Click "Upload Repository" to start the analysis

2. Interact with the Code:
   - Use the chat interface to ask questions about the code
   - Request documentation or explanations
   - Get optimization suggestions

3. View Analysis Results:
   - Repository summary
   - Code structure
   - Dependencies
   - Documentation

Project Structure
----------------
- app.py: Main Flask application
- utils/
  - code_analyzer.py: Code analysis and documentation generation
  - query_processor.py: Query handling and response generation
  - rag_processor.py: RAG system implementation
- static/
  - css/: Stylesheets
  - js/: JavaScript files
- templates/
  - index.html: Main web interface

Supported Languages
-----------------
- Python
- JavaScript/TypeScript
- React/JSX/TSX
- HTML
- CSS
- JSON
- Markdown
- Text files

Technical Details
----------------
- Uses sentence-transformers for embeddings
- FAISS for efficient similarity search
- OpenAI GPT-4 for response generation
- AST parsing for code analysis
- Advanced documentation generation
