# logger.py

import logging
import os

def setup_logger(log_path="bot.log"):
    if not os.path.exists(log_path):
        open(log_path, "w").close()
    logger = logging.getLogger("bot_logger")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(funcName)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    return logger

logger = setup_logger()
