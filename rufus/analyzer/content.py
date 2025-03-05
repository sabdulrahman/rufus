import logging
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

from ..utils.error import RufusError, handle_error

class ContentAnalyzer:
    """
    Content analyzer for determining relevance of extracted content to user instructions.
    """
    
    def __init__(self, api_key: str, config: Any):
        """
        Initialize the content analyzer.
        Args:
            api_key: API key for accessing LLM services (using OPEN_AI_KEY but reading as RUFUS_API_KEY)
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("rufus.analyzer")
        
        #Load environment variables
        load_dotenv()
        self.llm_provider = self.config.get('llm_provider', 'openai')
        
        #Use the provided API key first, then try the environment variable
        self.api_key = api_key or os.getenv('RUFUS_API_KEY')
        
        if self.llm_provider == 'openai':
            self.model = self.config.get('openai_model', 'gpt-4o-mini')
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
            else:
                self.client = OpenAI()
                self.logger.warning("No API key provided. Using env variables.")
        else:
            raise RufusError(f"Unsupported LLM provider: {self.llm_provider}")
    
    @handle_error
    def analyze(self, crawl_results: List[Dict[str, Any]], instructions: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze crawled content for relevance to user instructions.
        Args:
            crawl_results: Results from the crawler
            instructions: User instructions for content filtering
        Returns:
            List of relevant content with analysis metadata
        """
        if not crawl_results:
            return []
        
        self.logger.info(f"Analyzing {len(crawl_results)} pages for relevance")
        
        if not instructions:
            #If no instructions, return all content
            return crawl_results
        
        relevant_content = []
        
        for page in crawl_results:
            relevance_score, relevant_sections = self._assess_relevance(page, instructions)
            
            if relevance_score >= self.config.get('relevance_threshold', 0.3):
                #Add relevance analysis to page metadata
                page['metadata']['relevance'] = {
                    'score': relevance_score,
                    'relevant_sections': relevant_sections
                }
                
                #Keep only the relevant sections if specified
                if self.config.get('extract_relevant_only', True) and relevant_sections:
                    #Make sure relevant_sections contains only strings before joining
                    if relevant_sections and isinstance(relevant_sections, list):
                        #Convert any non-string items to strings
                        text_sections = []
                        for section in relevant_sections:
                            if isinstance(section, str):
                                text_sections.append(section)
                            elif isinstance(section, dict) and 'text' in section:
                                text_sections.append(section['text'])
                            elif isinstance(section, dict):
                                text_sections.append(json.dumps(section))
                            else:
                                text_sections.append(str(section))         
                        page['content']['filtered_text'] = '\n\n'.join(text_sections)
                    elif isinstance(relevant_sections, str):
                        page['content']['filtered_text'] = relevant_sections
                    else:
                        page['content']['filtered_text'] = str(relevant_sections)
                relevant_content.append(page)

        relevant_content.sort(key=lambda x: x['metadata']['relevance']['score'], reverse=True)        
        self.logger.info(f"Found {len(relevant_content)} relevant pages")
        return relevant_content
    
    def _assess_relevance(self, page: Dict[str, Any], instructions: str) -> tuple:
        """
        Assess the relevance of a page to the given instructions.
        Args:
            page: Page content and metadata
            instructions: User instructions
        Returns:
            Tuple of (relevance_score, list_of_relevant_sections)
        """
        self.logger.debug(f"Assessing relevance of {page['url']}")
        page_text = page['content']['text']
        
        # If the page is too long, split it into chunks for analysis
        max_chunk_length = self.config.get('max_chunk_length', 4000)
        if len(page_text) > max_chunk_length:
            chunks = self._split_text(page_text, max_chunk_length)
        else:
            chunks = [page_text]
        
        relevant_sections = []
        chunk_scores = []
        
        for chunk in chunks:
            if not chunk.strip():
                continue
                
            chunk_relevance, section_text = self._analyze_chunk(chunk, instructions)

            if chunk_relevance >= self.config.get('chunk_relevance_threshold', 0.5):
                chunk_scores.append(chunk_relevance)
                if section_text:
                    relevant_sections.append(section_text)
        if chunk_scores:
            relevance_score = sum(chunk_scores) / len(chunk_scores)
        else:
            relevance_score = 0.0
            
        return relevance_score, relevant_sections
    
    def _analyze_chunk(self, text: str, instructions: str) -> tuple:
        """
        Analyze a chunk of text for relevance to instructions using an LLM.
        
        Args:
            text: Text chunk to analyze
            instructions: User instructions
            
        Returns:
            Tuple of (relevance_score, extracted_relevant_text)
        """
        # Build prompt for LLM
        prompt = f"""
        You are an AI assistant that analyzes web content to determine its relevance to specific instructions.
        
        INSTRUCTIONS:
        {instructions}
        
        CONTENT:
        {text}
        
        TASK:
        1. Determine if this content is relevant to the instructions on a scale of 0.0 to 1.0.
        2. Extract only the sections that are directly relevant to the instructions.
        3. Provide your response in JSON format with the following structure:
        {{
            "relevance_score": [score between 0.0 and 1.0],
            "relevant_text": [extracted relevant text as a plain string, or null if none is relevant]
        }}
        """
        
        try:
            if self.llm_provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a content filtering assistant that determines relevance of web content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                
                # Get the content as a string from the message
                content = response.choices[0].message.content
                
                # Now we can use string methods on this content
                try:
                    # Try to parse it as JSON directly first
                    try:
                        result = json.loads(content)
                        relevance_score = float(result.get('relevance_score', 0.0))
                        relevant_text = result.get('relevant_text')
                        
                        # Ensure relevant_text is a string if it's not None
                        if relevant_text is not None and not isinstance(relevant_text, str):
                            if isinstance(relevant_text, list):
                                # If it's a list, join the elements
                                relevant_text = '\n\n'.join(str(item) for item in relevant_text)
                            else:
                                # Otherwise convert to string
                                relevant_text = str(relevant_text)
                        
                        return relevance_score, relevant_text
                    except json.JSONDecodeError:
                        # If direct parsing fails, try to extract JSON from the text
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_content = content[json_start:json_end]
                            result = json.loads(json_content)
                            
                            relevance_score = float(result.get('relevance_score', 0.0))
                            relevant_text = result.get('relevant_text')
                            
                            # Ensure relevant_text is a string if it's not None
                            if relevant_text is not None and not isinstance(relevant_text, str):
                                if isinstance(relevant_text, list):
                                    # If it's a list, join the elements
                                    relevant_text = '\n\n'.join(str(item) for item in relevant_text)
                                else:
                                    # Otherwise convert to string
                                    relevant_text = str(relevant_text)
                            
                            return relevance_score, relevant_text
                        else:
                            self.logger.warning("Could not find JSON in LLM response")
                            return 0.0, None
                        
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.error(f"Error parsing LLM response: {str(e)}")
                    return 0.0, None
                
        except Exception as e:
            self.logger.error(f"Error calling LLM API: {str(e)}")
            return 0.0, None
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """
        Split text into chunks of approximately equal length.
        Args:
            text: Text to split
            max_length: Maximum chunk length
        Returns:
            List of text chunks
        """
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            # If a single paragraph is too long, split it further
            if len(paragraph) > max_length:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if current_length + len(sentence) <= max_length:
                        current_chunk.append(sentence)
                        current_length += len(sentence) + 2  # Add 2 for '. '
                    else:
                        chunks.append('. '.join(current_chunk) + '.' if current_chunk else '')
                        current_chunk = [sentence]
                        current_length = len(sentence)
            else:
                if current_length + len(paragraph) <= max_length:
                    current_chunk.append(paragraph)
                    current_length += len(paragraph) + 2  # Add 2 for '\n\n'
                else:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [paragraph]
                    current_length = len(paragraph)
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks