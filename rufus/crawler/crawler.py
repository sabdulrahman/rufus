import logging
import time
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import asyncio
from .browser import HeadlessBrowser
import aiohttp

from ..utils.error import RufusError, handle_error
from .parser import HTMLParser

class Crawler:
    """
    Web crawler responsible for navigating websites and extracting HTML content.
    """
    
    def __init__(self, config):
        """
        Initialize the crawler.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("rufus.crawler")
        self.parser = HTMLParser()
        self.visited_urls = set()
        self.headers = {
            'User-Agent': config.get('user_agent', 'Rufus/1.0 (https://github.com/sabdulrahman/rufus)'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        # Add browser instance
        self.use_browser = config.get('use_browser', False)
        self.browser = None
        if self.use_browser:
            self.browser = HeadlessBrowser(config)        
    
    @handle_error
    async def crawl(self, start_url: str, max_pages: int = 10, depth: int = 2) -> List[Dict[str, Any]]:
        """
        Crawl a website starting from the given URL.
        
        Args:
            start_url: The starting URL for crawling
            max_pages: Maximum number of pages to crawl
            depth: Maximum depth of nested links to follow
            
        Returns:
            List of dictionaries containing page content and metadata
        """
        self.logger.info(f"Starting crawl at {start_url} with max_pages={max_pages} and depth={depth}")
        
        # Validate the URL
        parsed_url = urlparse(start_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise RufusError(f"Invalid URL: {start_url}")
        
        self.visited_urls = set()
        self.domain = parsed_url.netloc
        
        # Initialize browser if needed
        if self.use_browser:
            await self.browser.setup()
        
        # Choose between synchronous and asynchronous crawling based on config
        if self.config.get('async_crawling', True):
            try:
                return await self._async_crawl(start_url, max_pages, depth)
            finally:
                # Close browser if it was used
                if self.use_browser:
                    await self.browser.close()
        else:
            try:
                return await self._sync_crawl(start_url, max_pages, depth)
            finally:
                # Close browser if it was used
                if self.use_browser:
                    await self.browser.close()
    
    def _sync_crawl(self, start_url: str, max_pages: int, depth: int) -> List[Dict[str, Any]]:
        """
        Synchronous version of the crawling algorithm.
        """
        to_visit = [(start_url, 0)]  # (url, current_depth)
        results = []
        
        while to_visit and len(results) < max_pages:
            url, current_depth = to_visit.pop(0)
            
            if url in self.visited_urls:
                continue
                
            self.visited_urls.add(url)
            
            try:
                response = requests.get(url, headers=self.headers, 
                                       timeout=self.config.get('request_timeout', 10))
                response.raise_for_status()
                
                # Respect robots.txt and rate limiting
                time.sleep(self.config.get('crawl_delay', 1))
                
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract content
                content = self.parser.extract_content(soup)
                
                # Add to results
                results.append({
                    'url': url,
                    'title': self.parser.extract_title(soup),
                    'content': content,
                    'html': response.text if self.config.get('save_html', False) else None,
                    'metadata': {
                        'depth': current_depth,
                        'status_code': response.status_code,
                        'content_type': response.headers.get('Content-Type', ''),
                        'timestamp': time.time()
                    }
                })
                
                # If we haven't reached max depth, extract links and add to queue
                if current_depth < depth:
                    links = self.parser.extract_links(soup, base_url=url)
                    filtered_links = self._filter_links(links)
                    
                    for link in filtered_links:
                        if link not in self.visited_urls:
                            to_visit.append((link, current_depth + 1))
            
            except Exception as e:
                self.logger.error(f"Error crawling {url}: {str(e)}")
        
        return results
    
    async def _async_crawl(self, start_url: str, max_pages: int, depth: int) -> List[Dict[str, Any]]:
        """
        Asynchronous version of the crawling algorithm for better performance.
        """
        to_visit = [(start_url, 0)]  # (url, current_depth)
        results = []
        
        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.get('max_concurrent_requests', 5))
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while to_visit and len(results) < max_pages:
                # Process up to N URLs concurrently
                batch = to_visit[:self.config.get('batch_size', 5)]
                to_visit = to_visit[self.config.get('batch_size', 5):]
                
                # Create tasks for the batch
                tasks = [self._fetch_and_parse(session, url, current_depth, semaphore) 
                         for url, current_depth in batch if url not in self.visited_urls]
                
                # Mark URLs as visited
                self.visited_urls.update([url for url, _ in batch])
                
                # Execute tasks concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Error during async crawl: {str(result)}")
                        continue
                    
                    if result:
                        results.append(result['page_data'])
                        
                        # If we haven't reached max depth, add new links to queue
                        if result['current_depth'] < depth:
                            for link in result['links']:
                                if link not in self.visited_urls:
                                    to_visit.append((link, result['current_depth'] + 1))
        
        return results
    
    async def _fetch_and_parse(self, session, url: str, current_depth: int, semaphore) -> Dict[str, Any]:
        """
        Fetch a URL and parse its content asynchronously.
        """
        async with semaphore:
            try:
                # Use headless browser if configured
                if self.use_browser:
                    page_data = await self.browser.get_page_content(url)
                    html = page_data['html']
                    links = page_data['links']
                    
                    # Respect rate limiting
                    await asyncio.sleep(self.config.get('crawl_delay', 1))
                else:
                    # Use standard HTTP request
                    async with session.get(url, timeout=self.config.get('request_timeout', 10)) as response:
                        if response.status != 200:
                            self.logger.warning(f"Received status code {response.status} for {url}")
                            return None
                        
                        # Respect rate limiting
                        await asyncio.sleep(self.config.get('crawl_delay', 1))
                        
                        # Get the HTML content
                        html = await response.text()
                        links = None  # Will be extracted by parser
                
                # Parse the HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract content
                content = self.parser.extract_content(soup)
                
                # Extract links if not already extracted by browser
                if links is None:
                    links = self.parser.extract_links(soup, base_url=url)
                
                filtered_links = self._filter_links(links)
                
                return {
                    'page_data': {
                        'url': url,
                        'title': self.parser.extract_title(soup),
                        'content': content,
                        'html': html if self.config.get('save_html', False) else None,
                        'metadata': {
                            'depth': current_depth,
                            'status_code': 200,  # Browser always returns 200 if successful
                            'content_type': 'text/html',  # Assuming HTML content
                            'timestamp': time.time(),
                            'rendered': self.use_browser  # Flag to indicate if JS was rendered
                        }
                    },
                    'current_depth': current_depth,
                    'links': filtered_links
                }
            
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {str(e)}")
                return None
    
    def _filter_links(self, links: List[str]) -> List[str]:
        """
        Filter links to ensure they are valid and within the same domain.
        
        Args:
            links: List of links to filter
            
        Returns:
            Filtered list of links
        """
        filtered_links = []
        
        for link in links:
            parsed = urlparse(link)
            
            # Check if link is within the same domain, if stay_in_domain is True
            if self.config.get('stay_in_domain', True) and parsed.netloc != self.domain:
                continue
            
            # Skip URLs with irrelevant file extensions
            if any(link.endswith(ext) for ext in self.config.get('skip_extensions', ['.pdf', '.jpg', '.png', '.gif'])):
                continue
                
            # Skip URLs containing ignore patterns
            if any(pattern in link for pattern in self.config.get('ignore_patterns', [])):
                continue
                
            filtered_links.append(link)
            
        return filtered_links
    
    def reset(self) -> None:
        """
        Reset the crawler state.
        """
        self.visited_urls = set()