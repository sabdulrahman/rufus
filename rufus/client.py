import os
import logging
from typing import List, Dict, Any, Optional, Union

from .crawler.crawler import Crawler
from .analyzer.content import ContentAnalyzer
from .synthesizer.document import DocumentSynthesizer
from .utils.error import RufusError, handle_error
from .utils.config import Config

class RufusClient:
    """
    Main client for Rufus, a tool for intelligent web data extraction for LLMs.
    
    This client provides an interface for crawling websites based on user instructions
    and synthesizing the data into structured documents for RAG systems.
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Rufus client.
        
        Args:
            api_key: API key for accessing LLM services
            config: Optional configuration dictionary with custom settings
        """
        self.api_key = api_key or os.getenv('RUFUS_API_KEY')
        if not self.api_key:
            raise RufusError("API key is required. Set it either through the constructor or as an environment variable 'RUFUS_API_KEY'.")
        
        self.config = Config(config)
        self.logger = logging.getLogger("rufus")
        
        # Initialize components
        self.crawler = Crawler(self.config)
        self.analyzer = ContentAnalyzer(self.api_key, self.config)
        self.synthesizer = DocumentSynthesizer(self.config)
    
    @handle_error
    async def scrape(self, url: str, instructions: Optional[str] = None, max_pages: int = 10, 
               depth: int = 2, output_format: str = "json") -> Union[List[Dict[str, Any]], str]:
        """
        Scrape a website based on the given instructions and return structured documents.
        
        Args:
            url: The starting URL to scrape
            instructions: Instructions for what kind of information to extract
            max_pages: Maximum number of pages to crawl
            depth: Maximum depth of nested links to follow
            output_format: Format of the output documents ('json', 'text', 'csv')
            
        Returns:
            Structured documents containing the extracted information
        """
        self.logger.info(f"Starting scraping of {url} with instructions: {instructions}")
        
        # Step 1: Crawl the website and collect HTML content
        crawl_results = await self.crawler.crawl(url, max_pages=max_pages, depth=depth)
        
        if not crawl_results:
            self.logger.warning(f"No content found at {url}")
            return []
        
        # Step 2: Analyze content for relevance to instructions
        analyzed_content = await self.analyze_content(crawl_results, instructions)
        
        # Step 3: Synthesize the relevant content into structured documents
        documents = await self.synthesize_documents(analyzed_content, output_format)
        
        self.logger.info(f"Scraping complete. Generated {len(documents)} documents.")
        return documents
    
    async def analyze_content(self, crawl_results, instructions):
        """Wrapper for the content analysis to support async"""
        return self.analyzer.analyze(crawl_results, instructions)
    
    async def synthesize_documents(self, analyzed_content, output_format):
        """Wrapper for document synthesis to support async"""
        return self.synthesizer.synthesize(analyzed_content, output_format=output_format)
    
    @handle_error
    async def get_summary(self, documents: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the extracted documents.
        
        Args:
            documents: The documents to summarize
            
        Returns:
            A summary of the documents
        """
        return self.synthesizer.generate_summary(documents)
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Update the configuration settings.
        
        Args:
            config: New configuration settings
        """
        self.config.update(config)
        self.crawler.config = self.config
        self.analyzer.config = self.config
        self.synthesizer.config = self.config