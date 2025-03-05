import logging
import functools
import traceback
from typing import Callable, Any

class RufusError(Exception):
    """Base exception for all Rufus-related errors."""
    
    def __init__(self, message: str, code: str = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            code: Error code
        """
        self.message = message
        self.code = code
        super().__init__(message)

class CrawlerError(RufusError):
    """Exception raised during web crawling."""
    pass

class AnalysisError(RufusError):
    """Exception raised during content analysis."""
    pass

class SynthesisError(RufusError):
    """Exception raised during document synthesis."""
    pass

class APIError(RufusError):
    """Exception raised during API calls."""
    pass

def handle_error(func: Callable) -> Callable:
    """
    Decorator for handling errors in Rufus functions.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = logging.getLogger("rufus.error")
        
        try:
            return func(*args, **kwargs)
        except RufusError as e:
            # Log the error and re-raise
            logger.error(f"{type(e).__name__}: {e.message}")
            raise
        except Exception as e:
            # Log the unexpected error with traceback
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # Convert to RufusError and raise
            if "crawl" in func.__name__:
                raise CrawlerError(f"Error during web crawling: {str(e)}")
            elif "analyze" in func.__name__:
                raise AnalysisError(f"Error during content analysis: {str(e)}")
            elif "synthesize" in func.__name__:
                raise SynthesisError(f"Error during document synthesis: {str(e)}")
            else:
                raise RufusError(f"Unexpected error: {str(e)}")
    
    return wrapper

def format_error_response(error: Exception) -> dict:
    """
    Format an exception into a standardized error response.
    
    Args:
        error: The exception to format
        
    Returns:
        Formatted error response
    """
    if isinstance(error, RufusError):
        error_type = type(error).__name__
        message = error.message
        code = error.code
    else:
        error_type = "UnexpectedError"
        message = str(error)
        code = "unknown_error"
    
    return {
        "error": True,
        "error_type": error_type,
        "message": message,
        "error_code": code
    }