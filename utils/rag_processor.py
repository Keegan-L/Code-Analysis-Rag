import os
from typing import Dict, List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CodeChunk:
    def __init__(self, content: str, file_path: str, start_line: int, end_line: int, metadata: Optional[Dict] = None):
        self.content = content
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.metadata = metadata or {}
        self.embedding = None

class RAGProcessor:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG processor
        
        Args:
            model_name (str): Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.vector_index = None
        self.chunks = []
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI client with minimal configuration
        self.client = OpenAI(
            api_key=self.openai_api_key,
            timeout=30.0
        )
    
    def process_repository(self, files_data: Dict[str, Dict]) -> None:
        """
        Process a repository and create embeddings for code chunks
        
        Args:
            files_data (Dict[str, Dict]): Dictionary of file paths and their metadata
                Each value is a dict with 'content' key containing the file content
        """
        # Clear existing data
        self.chunks = []
        
        # Process each file
        for file_path, file_info in files_data.items():
            # Get the file content
            content = file_info['content']
            
            # Split file into chunks
            chunks = self._split_file_into_chunks(file_path, content)
            self.chunks.extend(chunks)
        
        # Create embeddings and build index
        self._create_embeddings()
        self._build_index()
    
    def _split_file_into_chunks(self, file_path: str, content: str) -> List[CodeChunk]:
        """
        Split a file into meaningful code chunks
        
        Args:
            file_path (str): Path to the file
            content (str): File content
            
        Returns:
            List[CodeChunk]: List of code chunks
        """
        chunks = []
        lines = content.split('\n')
        
        # Simple chunking strategy - split by functions and classes
        current_chunk = []
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            
            # Check for function or class definition
            if line.strip().startswith(('def ', 'class ')) and len(current_chunk) > 1:
                # Save previous chunk
                if len(current_chunk) > 1:
                    chunks.append(CodeChunk(
                        content='\n'.join(current_chunk[:-1]),
                        file_path=file_path,
                        start_line=start_line,
                        end_line=i-1
                    ))
                # Start new chunk
                current_chunk = [line]
                start_line = i
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(CodeChunk(
                content='\n'.join(current_chunk),
                file_path=file_path,
                start_line=start_line,
                end_line=len(lines)
            ))
        
        return chunks
    
    def _create_embeddings(self) -> None:
        """Create embeddings for all code chunks"""
        # Prepare texts for embedding
        texts = [chunk.content for chunk in self.chunks]
        
        # Create embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Store embeddings in chunks
        for chunk, embedding in zip(self.chunks, embeddings):
            chunk.embedding = embedding
    
    def _build_index(self) -> None:
        """Build FAISS index for efficient similarity search"""
        if not self.chunks:
            return
        
        # Get embedding dimension
        dim = len(self.chunks[0].embedding)
        
        # Create FAISS index
        self.vector_index = faiss.IndexFlatL2(dim)
        
        # Add embeddings to index
        embeddings = np.array([chunk.embedding for chunk in self.chunks]).astype('float32')
        self.vector_index.add(embeddings)
    
    def search(self, query: str, k: int = 5) -> List[Tuple[CodeChunk, float]]:
        """
        Search for relevant code chunks
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            List[Tuple[CodeChunk, float]]: List of (chunk, similarity score) tuples
        """
        if not self.vector_index:
            return []
        
        # Create query embedding
        query_embedding = self.model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search index
        distances, indices = self.vector_index.search(query_embedding, k)
        
        # Return results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(distance)))
        
        return results
    
    def answer_question(self, question: str, files_data: Dict[str, Dict]) -> Dict:
        """
        Answer a question about the codebase using RAG
        
        Args:
            question (str): The question to answer
            files_data (Dict[str, Dict]): Dictionary of file paths and their metadata
                Each value is a dict with 'content' key containing the file content
                
        Returns:
            Dict: Response containing answer and sources
        """
        if not self.vector_index:
            self.process_repository(files_data)
        
        # Get relevant code chunks
        relevant_chunks = self.search(question)
        
        # Prepare context from relevant chunks
        context = self._prepare_context(relevant_chunks)
        
        # Generate answer using OpenAI
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are an expert code analysis assistant. Your task is to provide different types of responses based on the question:

For high-level overview questions (e.g., "what does X file do?"):
- Provide a concise, high-level summary of the file's purpose and main functionality
- Focus on the big picture and key components
- Keep it brief and avoid technical details unless specifically asked

For specific library/function questions (e.g., "what does X library do?"):
- Explain the library's purpose and main functionality
- Reference specific lines where it's imported and used
- Show code snippets in a code editor style format:
  ```python
  # Example code snippet
  def example():
      pass
  ```
- Explain how it integrates with other parts of the codebase

For implementation details (e.g., "how does X work?"):
- Break down the code into understandable parts
- Reference specific lines and show relevant code snippets
- Explain the logic and flow
- Highlight important patterns or design decisions

Always:
- Be clear and concise
- Use appropriate technical terms
- Format code snippets nicely
- Reference specific lines when discussing implementation details
- Provide context when relevant"""},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nPlease analyze the code and provide an appropriate response based on the question type."}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            # Prepare sources
            sources = []
            for chunk, score in relevant_chunks:
                sources.append({
                    'file': chunk.file_path,
                    'lines': f"{chunk.start_line}-{chunk.end_line}",
                    'content': chunk.content,
                    'score': float(score)
                })
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': min(1.0, max(0.0, float(relevant_chunks[0][1]) if relevant_chunks else 0.0))
            }
            
        except Exception as e:
            return {
                'answer': f"Error generating answer: {str(e)}",
                'sources': [],
                'confidence': 0.0
            }
    
    def _prepare_context(self, relevant_chunks: List[Tuple[CodeChunk, float]]) -> str:
        """
        Prepare context from relevant code chunks
        
        Args:
            relevant_chunks (List[Tuple[CodeChunk, float]]): List of relevant chunks and their scores
            
        Returns:
            str: Formatted context
        """
        context = "Relevant code sections:\n\n"
        
        for chunk, score in relevant_chunks:
            context += f"File: {chunk.file_path} (Lines {chunk.start_line}-{chunk.end_line})\n"
            context += "```\n"
            context += chunk.content
            context += "\n```\n\n"
        
        return context 