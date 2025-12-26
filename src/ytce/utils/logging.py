from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger without duplicate handlers.
    
    Note: This logger may have handlers added elsewhere.
    Callers should check for existing handlers before adding new ones.
    """
    logger = logging.getLogger(name)
    # Don't add default handler here - let callers configure as needed
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
    return logger
