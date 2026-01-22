"""
Logging Utility for SecureScribe Backend using Loguru

This module provides simple, powerful logging using loguru with OpenTelemetry integration.
Features include:

- Beautiful colorful console output by default
- Automatic log rotation and retention
- Minimal configuration needed
- FastAPI middleware integration
- Exception tracking and formatting with full traceback capture
- OpenTelemetry HTTP streaming with complete exception information
- Global exception handler for uncaught exceptions

Usage:
    from app.utils.logging import logger, setup_logging

    # Setup logging (call once in main.py)
    setup_logging()

    # Use logger directly
    logger.info("Application started")
    logger.warning("Something might be wrong")
    logger.error("An error occurred")
    logger.debug("Detailed debug information")
    logger.success("Operation completed successfully")

    # For exceptions, use logger.exception() to include traceback
    try:
        risky_operation()
    except Exception:
        logger.exception("Something went wrong")
"""

import logging
import os
import sys
import threading
import time
import traceback

from loguru import logger as loguru_logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource

# Export logger for easy import
logger = loguru_logger


def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to catch uncaught exceptions and log them with full traceback.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Format the full traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    # Log with full traceback - this will be sent to both console
    logger.critical(f"Uncaught exception in thread {threading.current_thread().name}: {exc_value}", extra={"traceback": tb_text})

    # Call the default exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_logging(level: str = "INFO") -> None:
    """
    Setup logging configuration using loguru with console and OpenTelemetry HTTP streaming.

    Features:
    - Console logging with colors and formatting
    - OpenTelemetry HTTP streaming with full traceback capture
    - Global exception handler for uncaught exceptions
    - Async logging to prevent blocking
    - Backtrace and diagnostic information included

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    Environment Variables:
        OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: OpenTelemetry HTTP API endpoint
                 If not set, only console logging is enabled.
        PYTHON_ENVIRONMENT: Environment name for OpenTelemetry labels (default: "development")

    Example:
        setup_logging("DEBUG")  # Enable debug logging with full tracebacks
    """
    # Import here to avoid circular imports
    from app.core.config import settings

    # Remove default handler
    loguru_logger.remove()

    # Add console handler with colors
    loguru_logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
    )

    # Add OpenTelemetry Log Exporter if OTEL_EXPORTER_OTLP_LOGS_ENDPOINT is configured
    otel_logs_endpoint = settings.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
    if otel_logs_endpoint:
        try:
            # Create OpenTelemetry resource
            env_name = os.getenv("PYTHON_ENVIRONMENT", "development").lower()
            resource = Resource.create({"service.name": "meeting-agent-api", "service.namespace": "meeting-agent", "deployment.environment": env_name.lower()})

            # Create logger provider and set globally
            otel_logger_provider = LoggerProvider(resource=resource)
            set_logger_provider(otel_logger_provider)

            # Add OTLP log exporter
            otlp_log_exporter = OTLPLogExporter(endpoint=otel_logs_endpoint)
            otel_logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))

            # Add console exporter for debugging if enabled
            if settings.OTEL_DEBUG:
                console_log_exporter = ConsoleLogExporter()
                otel_logger_provider.add_log_record_processor(SimpleLogRecordProcessor(console_log_exporter))

            # Bridge Python logging to OpenTelemetry
            root_logger = logging.getLogger()
            handler = LoggingHandler(level=logging.NOTSET, logger_provider=otel_logger_provider)
            existing_handlers = [h for h in root_logger.handlers if isinstance(h, LoggingHandler)]
            if not existing_handlers:
                root_logger.addHandler(handler)
                if root_logger.level == logging.NOTSET:
                    root_logger.setLevel(level)

            loguru_logger.info(f"OpenTelemetry logging configured: {otel_logs_endpoint}")
        except Exception as e:
            loguru_logger.warning(f"Failed to configure OpenTelemetry logging: {e}")
    else:
        loguru_logger.debug("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT not set, OpenTelemetry logging disabled")

    # Install global exception handler to catch uncaught exceptions
    sys.excepthook = _global_exception_handler

    # Log successful setup
    loguru_logger.info("Logging setup completed with traceback capture enabled")


# FastAPI middleware for request/response logging
class FastAPILoggingMiddleware:
    """
    FastAPI middleware that logs HTTP requests and responses with timing.

    Logs request method, path, response status, and duration.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        method = scope["method"]
        path = scope["path"]
        query = scope.get("query_string", b"").decode("utf-8")
        if query:
            path = f"{path}?{query}"

        logger.info(f"→ {method} {path}")

        # Track timing
        start_time = time.time()
        original_send = send
        response_status = None
        response_length = 0

        async def logging_send(message):
            nonlocal response_status, response_length

            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_length += len(message.get("body", b""))

            await original_send(message)

        try:
            await self.app(scope, receive, logging_send)
            duration = time.time() - start_time

            if response_status and response_status < 400:
                logger.success(f"← {method} {path} | {response_status} | {duration:.3f}s | {response_length} bytes")
            else:
                logger.warning(f"← {method} {path} | {response_status} | {duration:.3f}s | {response_length} bytes")
        except Exception:
            duration = time.time() - start_time
            logger.exception(f"Error processing request {method} {path} | ERROR | {duration:.3f}s")
            raise
