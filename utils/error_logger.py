import logging
import traceback
from datetime import datetime

LOG_FILE = "app_error.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

import traceback
from datetime import datetime

def log_error(context: str, error: Exception):
    print(f"[{context}] {str(error)}\n{traceback.format_exc()}")

def log_warning(context: str, message: str):
    print(f"[{context}] {message}")

def log_info(context: str, message: str):
    print(f"[{context}] {message}")

def get_last_errors(n=20):
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except Exception as e:
        return [f"Error reading log file: {e}"]
