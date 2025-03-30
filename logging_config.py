"""
Logging configuration for FastAPI.
"""

import json
import logging
import sys
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    A formatter that outputs JSON strings after parsing the LogRecord.
    """

    def access_log(self, record: logging.LogRecord, log_data: Dict[str, Any]) -> str:
        """
        Format the access log into a JSON string.
        """
        try:
            # Parse the access log message which is typically in the format:
            # "IP:port - - [timestamp] "METHOD /path HTTP/version" status_code size"
            parts = record.getMessage().split()
            if len(parts) >= 7:
                client = parts[0]
                timestamp = parts[3].strip("[]")
                method = parts[5].strip('"')
                path = parts[6].strip('"')
                status_code = parts[8]
                size = parts[9]

                log_data.update(
                    {
                        "type": "http",
                        "client": client,
                        "method": method,
                        "path": path,
                        "status_code": int(status_code),
                        "size": int(size),
                        "timestamp": timestamp,
                    }
                )
        except (IndexError, ValueError):
            # If parsing fails, keep the original message
            pass

        return log_data

    def handle_httptools_impl_log(
        self, record: logging.LogRecord, log_data: Dict[str, Any]
    ) -> str:
        """
        Format the httptools_impl log into a JSON string.
        """
        try:
            # Parse the httptools_impl log message which is typically in the format:
            # "IP:port - "METHOD /path HTTP/version" status_code"
            parts = record.getMessage().split()
            if len(parts) >= 5:
                client = parts[0]
                method = parts[2].strip('"')
                path = parts[3].strip('"')
                status_code = parts[5]

                log_data.update(
                    {
                        "type": "http",
                        "client": client,
                        "method": method,
                        "path": path,
                        "status_code": int(status_code),
                    }
                )
                del log_data["message"]
        except (IndexError, ValueError):
            # If parsing fails, keep the original message
            pass

        return log_data

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the LogRecord into a JSON string.
        """
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.name == "uvicorn.access":
            if record.module == "httptools_impl":
                log_data = self.handle_httptools_impl_log(record, log_data)
            else:
                log_data = self.access_log(record, log_data)

        # Handle FastAPI HTTP error logs
        elif record.name == "uvicorn.error":
            log_data["type"] = "error"

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """
    Set up logging configuration.
    """
    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a JSON formatter
    json_formatter = JSONFormatter()

    # Create a stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(json_formatter)

    # Configure root logger
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)

    # Disable uvicorn's default logging
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("httptools_impl").handlers = []

    # Configure uvicorn loggers to use our handler
    uvicorn_loggers = [
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("httptools_impl"),
    ]

    for logger in uvicorn_loggers:
        logger.setLevel(logging.INFO)
        logger.addHandler(stream_handler)
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
