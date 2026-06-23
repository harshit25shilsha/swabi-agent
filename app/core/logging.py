"""
Centralized logging configuration for the Swabi AI Agent.
 
All modules should import and use the logger from here rather than
calling logging.getLogger() directly, so log format and level are
consistent across the whole application and can be changed in one
place.
 
Usage in any module:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("something happened")
    logger.error("something broke", exc_info=True)
"""


import logging
import sys
 
 
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
 
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
 
 
def configure_logging(level: str = "INFO"):
    """
    Configure the root logger with a structured format.
 
    Called once at app startup (see app/main.py lifespan handler).
    Any module using get_logger() after this point will inherit the
    configured handler and formatter.
    """
 
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        force=True
    )
 
 
def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger. Pass __name__ from the calling module so
    log lines show which module they came from, e.g.:
        app.graph.agent | Processing request for session abc123
        app.routers.agent | POST /agent/ session=abc123 user_id=3
    """
 
    return logging.getLogger(name)