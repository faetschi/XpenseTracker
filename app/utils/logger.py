import logging
import sys
from app.core.config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Creates and returns a configured logger instance.
    
    Args:
        name (str): The name of the logger, typically __name__.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Only add handler if the logger doesn't have one already to prevent duplicate logs
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    # Always set log level from config (in case it changed or wasn't set correctly)
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
        
    return logger
