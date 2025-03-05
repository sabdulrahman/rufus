import unittest
from unittest.mock import patch, MagicMock
from rufus.utils.config import Config
from rufus.analyzer.content import ContentAnalyzer

class TestContentAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = Config({"llm_provider": "openai"})
        self.analyzer = ContentAnalyzer("fake_api_key", self.config)
    
    def test_split_text(self):
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = self.analyzer._split_text(text, 15)
        self.assertEqual(len(chunks), 3)
    
    @patch('openai.ChatCompletion.create')
    def test_analyze_chunk(self, mock_create):
        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"relevance_score": 0.8, "relevant_text": "This is relevant."}')), ]
        mock_create.return_value = mock_response
        
        score, text = self.analyzer._analyze_chunk("Test content", "Find information about tests")
        self.assertEqual(score, 0.8)
        self.assertEqual(text, "This is relevant.")

if __name__ == "__main__":
    unittest.main()