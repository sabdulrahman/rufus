import unittest
from unittest.mock import MagicMock, patch
from rufus.utils.config import Config
from rufus.crawler.crawler import Crawler

class TestCrawler(unittest.TestCase):
    def setUp(self):
        self.config = Config({"async_crawling": False})
        self.crawler = Crawler(self.config)
    
    @patch('requests.get')
    def test_sync_crawl(self, mock_get):
        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Test content</p></body></html>"
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_response
        
        # Test the crawler
        results = self.crawler._sync_crawl("https://example.com", 1, 0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com")
        
    def test_filter_links(self):
        self.crawler.domain = "example.com"
        links = [
            "https://example.com/page1",
            "https://example.com/page2.pdf",
            "https://otherdomain.com/page3"
        ]
        filtered = self.crawler._filter_links(links)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0], "https://example.com/page1")

if __name__ == "__main__":
    unittest.main()