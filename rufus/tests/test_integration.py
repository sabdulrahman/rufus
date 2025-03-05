import unittest
from unittest.mock import patch, MagicMock
from rufus.client import RufusClient

class TestIntegration(unittest.TestCase):
    @patch('rufus.crawler.crawler.Crawler.crawl')
    @patch('rufus.analyzer.content.ContentAnalyzer.analyze')
    @patch('rufus.synthesizer.document.DocumentSynthesizer.synthesize')
    def test_scrape_flow(self, mock_synthesize, mock_analyze, mock_crawl):
        # Mock the crawler results
        mock_crawl.return_value = [{"url": "https://example.com", "title": "Example", "content": {"text": "Test content"}}]
        
        # Mock the analyzer results
        mock_analyze.return_value = mock_crawl.return_value
        
        # Mock the synthesizer results
        mock_synthesize.return_value = [{"id": "doc_1", "title": "Example", "content": "Test content"}]
        
        # Test the client
        client = RufusClient(api_key="fake_key")
        documents = client.scrape("https://example.com", "Test instructions")
        
        # Verify the flow
        self.assertEqual(len(documents), 1)
        mock_crawl.assert_called_once()
        mock_analyze.assert_called_once()
        mock_synthesize.assert_called_once()

if __name__ == "__main__":
    unittest.main()