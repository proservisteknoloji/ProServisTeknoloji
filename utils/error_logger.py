import logging
logger = logging.getLogger(__name__)
import os
import traceback
from datetime import datetime



def _get_log_file_path() -> str | None:
    return os.getenv('PROSERVIS_LOG_FILE')


def log_error(context: str, error: Exception):
    logger.error("[%s] %s\n%s", context, str(error), traceback.format_exc())


def log_warning(context: str, message: str):
    logger.warning("[%s] %s", context, message)


def log_info(context: str, message: str):
    logger.info("[%s] %s", context, message)


def get_last_errors(n=20):
    log_path = _get_log_file_path()
    if not log_path:
        return ["Log file path not configured"]
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except Exception as e:
        return [f"Error reading log file: {e}"]
