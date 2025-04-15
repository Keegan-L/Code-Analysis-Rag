import os
from typing import Dict, List, Optional
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMProcessor:
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        """
        Initialize the LLM processor with a specific model
        
        Args:
            model (str): The OpenAI model to use
        """
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        openai.api_key = self.api_key
        
    def generate_code_summary(self, code: str, language: str) -> str:
        """
        Generate a summary of a code file using the LLM
        
        Args:
            code (str): The code content
            language (str): The programming language
            
        Returns:
            str: A summary of the code
        """
        prompt = f"""Please analyze this {language} code and provide a concise summary:
        
{code}

Focus on:
1. Main purpose and functionality
2. Key functions and classes
3. Important patterns or design decisions
4. Any notable dependencies or external integrations

Keep the summary clear and concise."""
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a code analysis expert. Provide clear, concise summaries of code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def answer_code_question(self, 
                           question: str, 
                           code_context: Dict[str, str],
                           analysis_context: Dict) -> Dict:
        """
        Answer a question about code using the LLM
        
        Args:
            question (str): The user's question
            code_context (Dict[str, str]): Dictionary of file paths and their contents
            analysis_context (Dict): Repository analysis results
            
        Returns:
            Dict: Response containing answer and relevant code references
        """
        # Prepare context for the LLM
        context_prompt = self._prepare_context_prompt(code_context, analysis_context)
        
        prompt = f"""Context about the codebase:
{context_prompt}

Question: {question}

Please provide:
1. A clear answer to the question
2. References to specific code files and sections that support your answer
3. Any additional insights or related information that might be helpful

Format your response in a way that's easy to understand and reference."""
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a code analysis expert. Answer questions about code clearly and provide specific references."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return self._parse_llm_response(response.choices[0].message.content)
    
    def _prepare_context_prompt(self, 
                              code_context: Dict[str, str],
                              analysis_context: Dict) -> str:
        """
        Prepare a context prompt for the LLM
        
        Args:
            code_context (Dict[str, str]): Dictionary of file paths and their contents
            analysis_context (Dict): Repository analysis results
            
        Returns:
            str: Formatted context prompt
        """
        # Start with repository summary
        context = f"Repository Summary:\n{analysis_context.get('summary', 'No summary available')}\n\n"
        
        # Add file summaries
        context += "File Summaries:\n"
        for file_path, summary in analysis_context.get('file_summaries', {}).items():
            context += f"- {file_path}: {summary.get('language', 'Unknown')} file with {summary.get('total_lines', 0)} lines\n"
        
        # Add key code snippets
        context += "\nKey Code Snippets:\n"
        for file_path, content in code_context.items():
            # Only include the first 100 lines of each file to avoid token limits
            context += f"\nFile: {file_path}\n"
            context += "```\n"
            context += "\n".join(content.split("\n")[:100])
            context += "\n```\n"
        
        return context
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse the LLM response into a structured format
        
        Args:
            response (str): The raw LLM response
            
        Returns:
            Dict: Structured response with answer and code references
        """
        # Simple parsing - in a real implementation, you might want to use more sophisticated parsing
        return {
            'answer': response,
            'code_references': []  # This could be enhanced to extract specific code references
        } 