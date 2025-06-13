# utils/logger_config.py

import logging
from contextvars import ContextVar
from logging.config import dictConfig

from core.utils.constants import COLORS, RESET

trace_id_var = ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True


class ShortNameFormatter(logging.Formatter):
    def format(self, record):
        record.shortname = record.name.rsplit(".", 1)[-1]
        record.trace_id = getattr(record, "trace_id", "-")
        color = COLORS.get(record.levelname, "\033[97m")
        message = super().format(record)
        return f"{color}{message}{RESET}"


def setup_logger():
    LOG_FORMAT = "[%(levelname)s] %(asctime)s | trace_id: %(trace_id)s | %(shortname)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "short": {
                "()": ShortNameFormatter,
                "fmt": LOG_FORMAT,
                "datefmt": DATE_FORMAT
            }
        },
        "filters": {
            "trace_id": {
                "()": TraceIdFilter
            }
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "formatter": "short",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["trace_id"]
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["default"]
        },
        "loggers": {
            "uvicorn.error": {"level": "INFO", "handlers": ["default"], "propagate": False},
            "httpx": {"level": "WARNING", "handlers": ["default"], "propagate": False},
            "uvicorn.access": {"level": "WARNING", "handlers": ["default"], "propagate": False},
            "urllib3": {"level": "WARNING", "handlers": ["default"], "propagate": False},
            "firebase_admin": {"level": "WARNING", "handlers": ["default"], "propagate": False},
            "requests": {"level": "WARNING", "handlers": ["default"], "propagate": False},
        },
    })
