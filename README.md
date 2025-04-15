# Code Analysis RAG System

A powerful code analysis tool that combines Retrieval-Augmented Generation (RAG) with code analysis to help developers understand and document their codebases. This system allows you to upload code repositories and ask natural language questions about the code, receiving detailed answers with relevant code snippets.

## Features

- **Repository Analysis**: Upload and analyze entire code repositories
- **Natural Language Queries**: Ask questions about the code in plain English
- **Code Snippets**: Get relevant code snippets with line numbers and syntax highlighting
- **Documentation Generation**: Generate comprehensive documentation for your codebase
- **Smart Code Understanding**: Uses RAG to provide context-aware answers about your code

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Node.js and npm (for frontend development)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd code-analysis-rag
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following content:
```env
OPENAI_API_KEY=your_api_key_here
```

5. Install frontend dependencies:
```bash
cd static
npm install
cd ..
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Upload a Repository**:
   - Click "Choose a zip file" to select your code repository
   - Click "Upload and Process" to analyze the codebase

2. **Ask Questions**:
   - Type your question in the chat input
   - Press Enter or click "Send"
   - Receive detailed answers with relevant code snippets

3. **Generate Documentation**:
   - Click "Generate Documentation" to create comprehensive documentation
   - Download the generated documentation as a zip file

## Example Questions

- "What does this codebase do?"
- "How does the authentication system work?"
- "Show me the main API endpoints"
- "Explain the database schema"
- "What are the key dependencies?"

## Project Structure

```
code-analysis-rag/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/               # Frontend assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── templates/       # HTML templates
└── utils/               # Utility modules
    ├── code_analyzer.py # Code analysis logic
    ├── llm_processor.py # LLM integration
    └── rag_processor.py # RAG implementation
```
