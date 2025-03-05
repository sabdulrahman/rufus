import os
import time
import unittest
from rufus.client import RufusClient

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # Get API key from environment
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.skipTest("OPENAI_API_KEY environment variable not set")
        
        # Create client
        self.client = RufusClient(api_key=self.api_key)
    
    def test_simple_scrape(self):
        # Use a simple, reliable website
        url = "https://www.nasa.gov/mars/"
        instructions = "Find information about Mars exploration missions and their scientific discoveries."
        
        # Scrape with minimal settings
        documents = self.client.scrape(url, instructions, max_pages=1, depth=0)
        
        # Verify we got a document
        self.assertGreaterEqual(len(documents), 1)
        self.assertIn('content', documents[0])
        
        # Print summary for inspection
        print(self.client.get_summary(documents))

if __name__ == "__main__":
    unittest.main()