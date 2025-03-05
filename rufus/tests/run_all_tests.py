import unittest

# Import all test modules
from tests.test_config import TestConfig
from tests.test_parser import TestHTMLParser
from tests.test_crawler import TestCrawler
from tests.test_analyzer import TestContentAnalyzer
from tests.test_integration import TestIntegration

# Create a test suite
def create_test_suite():
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestConfig))
    test_suite.addTest(unittest.makeSuite(TestHTMLParser))
    test_suite.addTest(unittest.makeSuite(TestCrawler))
    test_suite.addTest(unittest.makeSuite(TestContentAnalyzer))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    
    return test_suite

if __name__ == "__main__":
    # Run the tests
    runner = unittest.TextTestRunner()
    runner.run(create_test_suite())