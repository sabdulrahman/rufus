import logging
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, NavigableString, Tag

class HTMLParser:
    """
    HTML parser for extracting content and links from web pages.
    """
    
    def __init__(self):
        """
        Initialize the HTML parser.
        """
        self.logger = logging.getLogger("rufus.parser")
        
        # Define elements that typically contain the main content
        self.content_tags = {
            'article', 'main', 'section', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'table', 'tr', 'td', 'th'
        }
        
        # Define elements to skip when extracting content
        self.skip_tags = {
            'script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer', 'header', 
            'aside', 'form', 'button', 'input', 'img'
        }
        
        # Define common ids and classes for content areas
        self.content_identifiers = {
            'id': {'content', 'main', 'article', 'post', 'main-content', 'page-content'},
            'class': {'content', 'article', 'post', 'main', 'main-content', 'page-content'}
        }
        
        # Define common ids and classes for areas to skip
        self.skip_identifiers = {
            'id': {'header', 'footer', 'sidebar', 'menu', 'nav', 'navigation', 'comments', 'advertisement'},
            'class': {'header', 'footer', 'sidebar', 'menu', 'nav', 'navigation', 'comments', 'ad', 'advertisement'}
        }
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract the title of the page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Title of the page
        """
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return "Untitled Page"
    
    def extract_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract the main content from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary with structured content
        """
        # Try to find the main content area
        main_content = self._find_main_content(soup)
        
        if not main_content:
            # If no main content area is found, use the body
            main_content = soup.body or soup
        
        # Extract structured content
        structured_content = {
            'title': self.extract_title(soup),
            'headings': self._extract_headings(main_content),
            'paragraphs': self._extract_paragraphs(main_content),
            'lists': self._extract_lists(main_content),
            'tables': self._extract_tables(main_content),
            'text': self._extract_clean_text(main_content)
        }
        
        return structured_content
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract all links from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL of the page
            
        Returns:
            List of absolute URLs
        """
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip anchor links, javascript, and mailto
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            
            # Normalize the URL
            parsed = urlparse(absolute_url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
                
            links.append(normalized_url)
        
        return list(set(links))  # Remove duplicates
    
    def _find_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Find the main content area of the page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Tag object representing the main content area
        """
        # Try to find by common semantic elements
        for tag in ['main', 'article', 'section']:
            content = soup.find(tag)
            if content:
                return content
        
        # Try to find by common content IDs
        for id_value in self.content_identifiers['id']:
            content = soup.find(id=id_value)
            if content:
                return content
        
        # Try to find by common content classes
        for class_value in self.content_identifiers['class']:
            content = soup.find(class_=class_value)
            if content:
                return content
        
        # Fallback: Find the div with the most paragraphs
        divs = soup.find_all('div')
        if divs:
            div_with_most_paragraphs = max(divs, key=lambda div: len(div.find_all('p')), default=None)
            if div_with_most_paragraphs and len(div_with_most_paragraphs.find_all('p')) > 2:
                return div_with_most_paragraphs
        
        return None
    
    def _extract_headings(self, content: Tag) -> Dict[str, List[str]]:
        """
        Extract all headings from the content.
        
        Args:
            content: Tag object representing the content area
            
        Returns:
            Dictionary with heading levels and their text
        """
        headings = {}
        
        for level in range(1, 7):
            heading_tags = content.find_all(f'h{level}')
            if heading_tags:
                headings[f'h{level}'] = [h.get_text(strip=True) for h in heading_tags]
        
        return headings
    
    def _extract_paragraphs(self, content: Tag) -> List[str]:
        """
        Extract all paragraphs from the content.
        
        Args:
            content: Tag object representing the content area
            
        Returns:
            List of paragraph texts
        """
        paragraphs = []
        
        for p in content.find_all('p'):
            # Skip empty paragraphs
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)
        
        return paragraphs
    
    def _extract_lists(self, content: Tag) -> List[Dict[str, List[str]]]:
        """
        Extract all lists from the content.
        
        Args:
            content: Tag object representing the content area
            
        Returns:
            List of dictionaries containing list type and items
        """
        lists = []
        
        for list_tag in content.find_all(['ul', 'ol']):
            list_type = 'unordered' if list_tag.name == 'ul' else 'ordered'
            items = [li.get_text(strip=True) for li in list_tag.find_all('li') if li.get_text(strip=True)]
            
            if items:
                lists.append({
                    'type': list_type,
                    'items': items
                })
        
        return lists
    
    def _extract_tables(self, content: Tag) -> List[Dict[str, any]]:
        """
        Extract all tables from the content.
        
        Args:
            content: Tag object representing the content area
            
        Returns:
            List of dictionaries containing table structure
        """
        tables = []
        
        for table_tag in content.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Extract headers
            thead = table_tag.find('thead')
            if thead:
                th_tags = thead.find_all('th')
                if th_tags:
                    table_data['headers'] = [th.get_text(strip=True) for th in th_tags]
            
            if not table_data['headers']:
                # Try to get headers from first row if no thead
                first_row = table_tag.find('tr')
                if first_row:
                    th_tags = first_row.find_all('th')
                    if th_tags:
                        table_data['headers'] = [th.get_text(strip=True) for th in th_tags]
            
            # Extract rows
            tbody = table_tag.find('tbody') or table_tag
            for tr in tbody.find_all('tr'):
                # Skip if this is a header row we've already processed
                if tr == first_row and table_data['headers']:
                    continue
                    
                row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if row:
                    table_data['rows'].append(row)
            
            if table_data['headers'] or table_data['rows']:
                tables.append(table_data)
        
        return tables
    
    def _extract_clean_text(self, content: Tag) -> str:
        """
        Extract clean text content from the tag, excluding unwanted elements.
        
        Args:
            content: Tag object representing the content area
            
        Returns:
            Clean text content
        """
        # Make a copy to avoid modifying the original
        content_copy = BeautifulSoup(str(content), 'html.parser')
        
        # Remove unwanted elements
        for tag in self.skip_tags:
            for element in content_copy.find_all(tag):
                element.decompose()
        
        # Remove elements with unwanted IDs or classes
        for attribute, values in self.skip_identifiers.items():
            for value in values:
                for element in content_copy.find_all(attrs={attribute: lambda x: x and value in x.split()}):
                    element.decompose()
        
        # Get text with newlines
        text = ''
        for element in content_copy.descendants:
            if isinstance(element, NavigableString):
                parent = element.parent
                if parent and parent.name not in self.skip_tags:
                    text += str(element)
            elif element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'br']:
                text += '\n'
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n')]
        clean_text = '\n'.join(line for line in lines if line)
        
        return clean_text