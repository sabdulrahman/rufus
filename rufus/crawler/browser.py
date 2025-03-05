import logging
from typing import Dict, Optional, Any
import asyncio
from urllib.parse import urljoin

class HeadlessBrowser:
    """
    Headless browser integration for Rufus to handle JavaScript-rendered content.
    Supports Playwright and Selenium.
    """
    
    def __init__(self, config):
        """
        Initialize the headless browser handler.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("rufus.browser")
        self.browser_type = self.config.get('browser_type', 'playwright')
        self.browser = None
        self.context = None
        
    async def setup(self):
        """Initialize the browser based on configuration."""
        if self.browser_type == 'playwright':
            await self._setup_playwright()
        elif self.browser_type == 'selenium':
            self._setup_selenium()
        else:
            self.logger.warning(f"Unsupported browser type: {self.browser_type}. Falling back to Playwright.")
            await self._setup_playwright()
    
    async def _setup_playwright(self):
        """Set up Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            browser_options = {
                'headless': True,
                'slow_mo': self.config.get('browser_slow_mo', 50)
            }
            
            if self.config.get('browser_executable_path'):
                browser_options['executable_path'] = self.config.get('browser_executable_path')
                
            # Use chromium by default, but allow configuration
            browser_name = self.config.get('playwright_browser', 'chromium')
            if browser_name == 'firefox':
                self.browser = await self.playwright.firefox.launch(**browser_options)
            elif browser_name == 'webkit':
                self.browser = await self.playwright.webkit.launch(**browser_options)
            else:
                self.browser = await self.playwright.chromium.launch(**browser_options)
            
            # Create a browser context with user agent
            self.context = await self.browser.new_context(
                user_agent=self.config.get('user_agent', 'Rufus/1.0')
            )
            
            self.logger.info(f"Playwright {browser_name} browser initialized")
        except ImportError:
            self.logger.error("Playwright not installed. Please install with: pip install playwright")
            self.logger.error("Then install browsers with: playwright install")
            raise
    
    def _setup_selenium(self):
        """Set up Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument(f'user-agent={self.config.get("user_agent", "Rufus/1.0")}')
            
            if self.config.get('browser_executable_path'):
                service = Service(executable_path=self.config.get('browser_executable_path'))
                self.browser = webdriver.Chrome(service=service, options=options)
            else:
                self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            self.logger.info("Selenium Chrome WebDriver initialized")
        except ImportError:
            self.logger.error("Selenium not installed. Please install with: pip install selenium webdriver-manager")
            raise
    
    async def get_page_content(self, url: str) -> Dict[str, Any]:
        """
        Get the fully rendered page content using a headless browser.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with HTML content and links
        """
        if self.browser_type == 'playwright':
            return await self._get_with_playwright(url)
        else:
            return self._get_with_selenium(url)
    
    async def _get_with_playwright(self, url: str) -> Dict[str, Any]:
        """Get page content using Playwright."""
        try:
            # Create a new page
            page = await self.context.new_page()
            
            # Set timeout
            page.set_default_timeout(self.config.get('browser_timeout', 30000))
            
            # Navigate to URL
            await page.goto(url, wait_until=self.config.get('playwright_wait_until', 'networkidle'))
            
            # Wait for content to load (optional additional wait)
            if self.config.get('browser_wait_for_selector'):
                try:
                    await page.wait_for_selector(self.config.get('browser_wait_for_selector'), 
                                               state='attached', 
                                               timeout=5000)
                except:
                    # Continue even if selector not found
                    pass
            
            # Optional wait time
            if self.config.get('browser_wait_time'):
                await asyncio.sleep(self.config.get('browser_wait_time'))
            
            # Get page content
            html = await page.content()
            
            # Extract links if requested
            links = []
            if self.config.get('extract_links', True):
                link_elements = await page.query_selector_all('a[href]')
                for link in link_elements:
                    href = await link.get_attribute('href')
                    if href:
                        # Convert to absolute URL
                        absolute_url = urljoin(url, href)
                        links.append(absolute_url)
            
            # Close the page
            await page.close()
            
            return {
                'html': html,
                'links': links
            }
        except Exception as e:
            self.logger.error(f"Error fetching {url} with Playwright: {str(e)}")
            return {'html': '', 'links': []}
    
    def _get_with_selenium(self, url: str) -> Dict[str, Any]:
        """Get page content using Selenium."""
        try:
            # Set page load timeout
            self.browser.set_page_load_timeout(self.config.get('browser_timeout', 30))
            
            # Navigate to URL
            self.browser.get(url)
            
            # Wait for content to load (optional additional wait)
            if self.config.get('browser_wait_time'):
                import time
                time.sleep(self.config.get('browser_wait_time'))
            
            # Get page content
            html = self.browser.page_source
            
            # Extract links if requested
            links = []
            if self.config.get('extract_links', True):
                link_elements = self.browser.find_elements_by_tag_name('a')
                for link in link_elements:
                    href = link.get_attribute('href')
                    if href:
                        links.append(href)
            
            return {
                'html': html,
                'links': links
            }
        except Exception as e:
            self.logger.error(f"Error fetching {url} with Selenium: {str(e)}")
            return {'html': '', 'links': []}
    
    async def close(self):
        """Close the browser and release resources."""
        if self.browser_type == 'playwright':
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        else:
            if self.browser:
                self.browser.quit()
        
        self.logger.info("Browser closed and resources released")