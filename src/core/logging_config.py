import logging
import sys

from core.config import app_settings

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | " "%(filename)s:%(lineno)d | %(message)s"
)


def setup_logger() -> logging.Logger:
    """
    Setup and return the application logger.

    :return: Configured logger instance
    :rtype: logging.Logger
    """
    logger = logging.getLogger("rasbpi-homesystem")

    if logger.handlers:
        return logger  # Logger is already configured

    log_lvl = getattr(logging, app_settings.LOG_LEVEL.upper(), logging.INFO)

    logger.setLevel(log_lvl)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_lvl)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(handler)

    return logger
