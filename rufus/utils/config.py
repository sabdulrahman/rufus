import logging
import os
import json
from typing import Dict, Any, Optional

class Config:
    """
    Configuration handler for Rufus.
    
    This class manages configuration settings for the Rufus web crawler, content analyzer,
    and document synthesizer. It provides defaults and allows for customization.
    """
    
    # Default configuration settings
    DEFAULT_CONFIG = {
        # General settings
        "log_level": "INFO",
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        
        # Crawler settings
        "user_agent": "Rufus/1.0 (https://github.com/sabdulrahman/rufus)",
        "request_timeout": 10,
        "crawl_delay": 1,
        "max_concurrent_requests": 5,
        "batch_size": 5,
        "save_html": False,
        "stay_in_domain": True,
        "skip_extensions": [".pdf", ".jpg", ".png", ".gif", ".zip", ".exe"],
        "ignore_patterns": ["login", "signup", "cart", "checkout", "account"],
        "async_crawling": True,
        
        # Content analyzer settings
        "llm_provider": "openai",
        "openai_model": "gpt-4o-mini",
        "relevance_threshold": 0.3,
        "chunk_relevance_threshold": 0.5,
        "max_chunk_length": 4000,
        "extract_relevant_only": True,
        
        # Document synthesizer settings
        "use_llm_for_synthesis": True,
        "group_by_domain": False,
        "group_by_topic": False,
        "max_synthesis_chars_per_page": 3000,

        #Browser settings
        "use_browser": False,
        "browser_type": "playwright",  # or "selenium"
        "playwright_browser": "chromium",  # or "firefox", "webkit"
        "playwright_wait_until": "networkidle",  # or "load", "domcontentloaded"
        "browser_timeout": 30000,  # milliseconds
        "browser_wait_time": 0,  # additional seconds to wait after load
        "browser_wait_for_selector": "body",  # optional selector to wait for
        "browser_slow_mo": 50  # slow down browser operations by ms        
    }
    
    def __init__(self, custom_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration with defaults and custom settings.
        
        Args:
            custom_config: Custom configuration settings to override defaults
        """
        self.logger = logging.getLogger("rufus.config")
        
        # Start with default config
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from environment variables
        self._load_from_env()
        
        # Apply custom config if provided
        if custom_config:
            self.update(custom_config)
        
        # Configure logging
        self._configure_logging()
        
        self.logger.debug("Configuration initialized")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        Environment variables should be prefixed with RUFUS_.
        """
        for key, value in os.environ.items():
            if key.startswith("RUFUS_"):
                config_key = key[6:].lower()
                
                # Handle different types of values
                if value.lower() in ('true', 'yes', '1'):
                    self.config[config_key] = True
                elif value.lower() in ('false', 'no', '0'):
                    self.config[config_key] = False
                elif value.isdigit():
                    self.config[config_key] = int(value)
                elif value.replace('.', '', 1).isdigit():
                    self.config[config_key] = float(value)
                elif value.startswith('[') or value.startswith('{'):
                    try:
                        self.config[config_key] = json.loads(value)
                    except json.JSONDecodeError:
                        self.config[config_key] = value
                else:
                    self.config[config_key] = value
    
    def _configure_logging(self) -> None:
        """Configure logging based on the current configuration."""
        log_level_name = self.config.get('log_level', 'INFO')
        log_format = self.config.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Convert string log level to numeric value
        log_level = getattr(logging, log_level_name.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
    
    def update(self, new_config: Dict[str, Any]) -> None:
        """
        Update the configuration with new settings.
        
        Args:
            new_config: New configuration settings to apply
        """
        self.config.update(new_config)
        
        # Reconfigure logging if log level or format changed
        if 'log_level' in new_config or 'log_format' in new_config:
            self._configure_logging()
            
        self.logger.debug("Configuration updated")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """
        Get a configuration value using dictionary syntax.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value
            
        Raises:
            KeyError: If key is not found
        """
        return self.config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dictionary syntax.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the current configuration as a dictionary.
        
        Returns:
            Dictionary of configuration settings
        """
        return self.config.copy()