# app/services/logging_config.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Resolve project root directory dynamically (C:\VetMind AI)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE_PATH = LOG_DIR / "vetmind_errors.log"

def setup_logger(name: str = "VetMindAI") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Formatter showing Timestamp, Level, Module, Function, Line Number, & Message
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console Handler (Prints to terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (Writes error tracebacks to logs/vetmind_errors.log)
        file_handler = RotatingFileHandler(
            filename=LOG_FILE_PATH,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Single logger instance to import across modules
logger = setup_logger()