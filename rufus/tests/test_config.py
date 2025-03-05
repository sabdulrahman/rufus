import os
import unittest
from rufus.utils.config import Config

class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = Config()
        self.assertEqual(config.get("log_level"), "INFO")
        self.assertTrue(config.get("stay_in_domain"))
    
    def test_custom_config(self):
        custom = {"log_level": "DEBUG", "stay_in_domain": False}
        config = Config(custom)
        self.assertEqual(config.get("log_level"), "DEBUG")
        self.assertFalse(config.get("stay_in_domain"))
    
    def test_env_variables(self):
        os.environ["RUFUS_TEST_VAR"] = "test_value"
        config = Config()
        self.assertEqual(config.get("test_var"), "test_value")
        del os.environ["RUFUS_TEST_VAR"]

if __name__ == "__main__":
    unittest.main()