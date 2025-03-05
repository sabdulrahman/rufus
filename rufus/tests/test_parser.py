import unittest
from bs4 import BeautifulSoup
from rufus.crawler.parser import HTMLParser

class TestHTMLParser(unittest.TestCase):
    def setUp(self):
        self.parser = HTMLParser()
        self.html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome to Test Page</h1>
                <main>
                    <p>This is a test paragraph.</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                    <a href="/link1">Link 1</a>
                    <a href="https://example.com/link2">Link 2</a>
                </main>
            </body>
        </html>
        """
        self.soup = BeautifulSoup(self.html, 'html.parser')
    
    def test_extract_title(self):
        title = self.parser.extract_title(self.soup)
        self.assertEqual(title, "Test Page")
    
    def test_extract_content(self):
        content = self.parser.extract_content(self.soup)
        self.assertEqual(content["title"], "Test Page")
        self.assertTrue("This is a test paragraph." in content["paragraphs"])
        self.assertEqual(len(content["lists"]), 1)
    
    def test_extract_links(self):
        links = self.parser.extract_links(self.soup, "https://example.com")
        self.assertEqual(len(links), 2)
        self.assertTrue("https://example.com/link1" in links)
        self.assertTrue("https://example.com/link2" in links)

if __name__ == "__main__":
    unittest.main()