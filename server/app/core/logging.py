import logging
from logging import Formatter, LogRecord
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
import uuid

from .config import settings


# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record: LogRecord) -> str:
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        correlation_id = correlation_id_var.get()
        
        # Build the log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context if available
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = user_id
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
            
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add custom attributes
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", 
                          "funcName", "levelname", "levelno", "lineno", 
                          "module", "msecs", "pathname", "process", 
                          "processName", "relativeCreated", "thread", 
                          "threadName", "exc_info", "exc_text", "stack_info",
                          "extra_fields"]:
                log_entry[key] = value
                
        return json.dumps(log_entry)


class TextFormatter(Formatter):
    """Human-readable formatter for development"""
    
    def format(self, record: LogRecord) -> str:
        # Get context variables
        request_id = request_id_var.get()
        
        # Build context string
        context_parts = []
        if request_id:
            context_parts.append(f"req_id={request_id[:8]}")
            
        context_str = f"[{' '.join(context_parts)}] " if context_parts else ""
        
        # Format the message
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{record.levelname:8}"
        location = f"{record.name}:{record.funcName}:{record.lineno}"
        
        message = f"{timestamp} | {level} | {location} | {context_str}{record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
            
        return message


class AppLogger:
    """
    Centralized logging system with:
    - Structured logging (JSON format for production)
    - Context injection (request ID, user ID, etc.)
    - Multiple handlers (console, file, external services)
    - Log levels per environment
    - Performance metrics logging
    - Error tracking integration
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
        
    def _setup_logger(self):
        """Setup logger with handlers and formatters"""
        # Clear existing handlers
        self.logger.handlers = []
        self.logger.setLevel(getattr(logging, settings.logging_config.level))
        
        # Setup formatters
        if settings.logging_config.format == "json":
            formatter = StructuredFormatter()
        else:
            formatter = TextFormatter()
            
        # Console handler
        if "console" in settings.logging_config.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
        # File handler
        if "file" in settings.logging_config.handlers:
            log_dir = Path(settings.logging_config.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                settings.logging_config.file_path,
                maxBytes=settings.logging_config.max_file_size,
                backupCount=settings.logging_config.backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        # Prevent propagation to root logger
        self.logger.propagate = False
        
    def _add_context(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Add context variables to extra fields"""
        if settings.logging_config.include_context:
            extra["request_id"] = request_id_var.get()
            extra["user_id"] = user_id_var.get()
            extra["correlation_id"] = correlation_id_var.get()
        return extra
        
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        extra = self._add_context(kwargs)
        self.logger.debug(message, extra={"extra_fields": extra})
        
    def info(self, message: str, **kwargs):
        """Log info message"""
        extra = self._add_context(kwargs)
        self.logger.info(message, extra={"extra_fields": extra})
        
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        extra = self._add_context(kwargs)
        self.logger.warning(message, extra={"extra_fields": extra})
        
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message"""
        extra = self._add_context(kwargs)
        if error:
            extra["error_type"] = type(error).__name__
            extra["error_message"] = str(error)
            self.logger.error(message, exc_info=True, extra={"extra_fields": extra})
        else:
            self.logger.error(message, extra={"extra_fields": extra})
            
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        extra = self._add_context(kwargs)
        self.logger.critical(message, extra={"extra_fields": extra})
        
    def log_api_request(
        self, 
        endpoint: str, 
        method: str, 
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ):
        """Log API requests with metadata"""
        self.info(
            f"API Request: {method} {endpoint}",
            endpoint=endpoint,
            method=method,
            client_ip=client_ip,
            user_agent=user_agent,
            **kwargs
        )
        
    def log_api_response(
        self, 
        status_code: int, 
        response_time: float,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        """Log API responses with performance metrics"""
        level = "info" if 200 <= status_code < 400 else "warning"
        getattr(self, level)(
            f"API Response: {status_code}",
            status_code=status_code,
            response_time_ms=round(response_time * 1000, 2),
            endpoint=endpoint,
            **kwargs
        )
        
    def log_external_api_call(
        self, 
        service: str, 
        endpoint: str,
        method: str = "GET",
        **kwargs
    ):
        """Log external API interactions"""
        self.info(
            f"External API Call: {service}",
            service=service,
            endpoint=endpoint,
            method=method,
            **kwargs
        )
        
    def log_external_api_response(
        self,
        service: str,
        status_code: int,
        response_time: float,
        **kwargs
    ):
        """Log external API response"""
        level = "info" if 200 <= status_code < 400 else "warning"
        getattr(self, level)(
            f"External API Response: {service} - {status_code}",
            service=service,
            status_code=status_code,
            response_time_ms=round(response_time * 1000, 2),
            **kwargs
        )
        
    def log_cache_hit(self, key: str, **kwargs):
        """Log cache hit"""
        self.debug(
            "Cache hit",
            cache_key=key,
            cache_event="hit",
            **kwargs
        )
        
    def log_cache_miss(self, key: str, **kwargs):
        """Log cache miss"""
        self.debug(
            "Cache miss",
            cache_key=key,
            cache_event="miss",
            **kwargs
        )
        
    def log_business_event(self, event_type: str, data: Dict[str, Any]):
        """Log business-specific events"""
        self.info(
            f"Business Event: {event_type}",
            event_type=event_type,
            event_data=data
        )
        
    def log_performance_metric(
        self, 
        operation: str, 
        duration: float,
        success: bool = True,
        **kwargs
    ):
        """Log performance metrics"""
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            success=success,
            **kwargs
        )
        
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any]
    ):
        """Log security-related events"""
        level = {
            "low": "info",
            "medium": "warning",
            "high": "error",
            "critical": "critical"
        }.get(severity, "warning")
        
        getattr(self, level)(
            f"Security Event: {event_type}",
            security_event=event_type,
            severity=severity,
            details=details
        )


# Logger factory function
def get_logger(name: str) -> AppLogger:
    """Get a logger instance for the given name"""
    return AppLogger(name)


# Utility functions for context management
def set_request_id(request_id: str):
    """Set request ID for the current context"""
    request_id_var.set(request_id)
    
def set_user_id(user_id: str):
    """Set user ID for the current context"""
    user_id_var.set(user_id)
    
def set_correlation_id(correlation_id: str):
    """Set correlation ID for the current context"""
    correlation_id_var.set(correlation_id)
    
def generate_request_id() -> str:
    """Generate a new request ID"""
    return str(uuid.uuid4())
    
def clear_context():
    """Clear all context variables"""
    request_id_var.set(None)
    user_id_var.set(None)
    correlation_id_var.set(None)