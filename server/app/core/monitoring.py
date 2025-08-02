import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from typing import Dict, Any, Optional, List
from enum import Enum
import time
from functools import wraps
import asyncio

from .config import settings
from .logging import get_logger, request_id_var, user_id_var


logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorMonitoring:
    """Centralized error monitoring with Sentry"""
    
    @staticmethod
    def init_sentry(app_settings: Optional[Any] = None):
        """Initialize Sentry SDK with custom configuration"""
        config = app_settings or settings
        
        if not config.sentry_dsn:
            logger.warning("Sentry DSN not configured, error monitoring disabled")
            return
            
        # Don't initialize in development unless explicitly enabled
        if config.environment == "development" and not config.logging.sentry_enabled:
            logger.info("Sentry disabled in development environment")
            return
            
        try:
            sentry_sdk.init(
                dsn=config.sentry_dsn,
                environment=config.sentry_environment or config.environment,
                integrations=[
                    FastApiIntegration(
                        transaction_style="endpoint"
                    ),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                    HttpxIntegration(),
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    ),
                ],
                traces_sample_rate=config.sentry_traces_sample_rate,
                profiles_sample_rate=config.sentry_profiles_sample_rate,
                attach_stacktrace=config.logging.sentry_attach_stacktrace,
                send_default_pii=config.logging.sentry_send_default_pii,
                before_send=ErrorMonitoring._before_send,
                before_send_transaction=ErrorMonitoring._before_send_transaction,
                release=config.api.version,
                server_name=config.api.title,
                max_breadcrumbs=50,
                debug=config.debug,
            )
            
            logger.info(
                "Sentry initialized",
                environment=config.environment,
                traces_sample_rate=config.sentry_traces_sample_rate
            )
            
        except Exception as e:
            logger.error("Failed to initialize Sentry", error=e)
    
    @staticmethod
    def _before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter sensitive data before sending to Sentry"""
        # Skip certain errors in development
        if settings.environment == "development":
            if "exc_info" in hint:
                exc_type, exc_value, tb = hint["exc_info"]
                # Skip common development errors
                if exc_type.__name__ in ["KeyboardInterrupt", "SystemExit"]:
                    return None
                    
        # Remove sensitive headers
        if "request" in event and "headers" in event["request"]:
            sensitive_headers = [
                "authorization", "api-key", "x-api-key", 
                "cookie", "session", "token", "secret"
            ]
            headers = event["request"]["headers"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[REDACTED]"
                    
        # Remove sensitive query parameters
        if "request" in event and "query_string" in event["request"]:
            query_string = event["request"]["query_string"]
            sensitive_params = ["api_key", "token", "secret", "password"]
            for param in sensitive_params:
                if param in query_string:
                    # Simple redaction - in production use proper query parsing
                    query_string = query_string.replace(
                        f"{param}=", f"{param}=[REDACTED]"
                    )
            event["request"]["query_string"] = query_string
            
        # Remove sensitive data from extra context
        if "extra" in event:
            sensitive_keys = [
                "password", "token", "secret", "api_key", 
                "private_key", "credit_card", "ssn"
            ]
            for key in list(event["extra"].keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    event["extra"][key] = "[REDACTED]"
                    
        # Add request context
        request_id = request_id_var.get()
        if request_id:
            event.setdefault("tags", {})["request_id"] = request_id
            
        return event
    
    @staticmethod
    def _before_send_transaction(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter transactions before sending"""
        # Skip health check transactions
        if "transaction" in event and event["transaction"] in ["/health", "/api/health"]:
            return None
            
        # Add custom context
        request_id = request_id_var.get()
        if request_id:
            event.setdefault("tags", {})["request_id"] = request_id
            
        return event
    
    @staticmethod
    def capture_exception(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
        fingerprint: Optional[List[str]] = None
    ):
        """Capture exception with additional context"""
        with sentry_sdk.push_scope() as scope:
            # Set level
            scope.level = level
            
            # Add custom context
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
                    
            # Add user context if available
            user_id = user_id_var.get()
            if user_id:
                scope.set_user({"id": user_id})
                
            # Add request ID tag
            request_id = request_id_var.get()
            if request_id:
                scope.set_tag("request_id", request_id)
                
            # Set custom fingerprint for grouping
            if fingerprint:
                scope.fingerprint = fingerprint
                
            # Capture the exception
            sentry_sdk.capture_exception(error)
            
    @staticmethod
    def capture_message(
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
        fingerprint: Optional[List[str]] = None
    ):
        """Capture custom messages/events"""
        with sentry_sdk.push_scope() as scope:
            # Add context
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
                    
            # Add request context
            request_id = request_id_var.get()
            if request_id:
                scope.set_tag("request_id", request_id)
                
            # Set fingerprint
            if fingerprint:
                scope.fingerprint = fingerprint
                
            sentry_sdk.capture_message(message, level=level)
            
    @staticmethod
    def add_breadcrumb(
        message: str,
        category: str = "custom",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """Add breadcrumb for context"""
        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data or {}
        )
        
    @staticmethod
    def set_user_context(
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Set user context for error tracking"""
        user_data = {
            "id": user_id,
            "email": email,
            "username": username,
            "ip_address": ip_address
        }
        
        # Remove None values
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        # Add extra data
        if extra:
            user_data.update(extra)
            
        sentry_sdk.set_user(user_data)
        
    @staticmethod
    def clear_context():
        """Clear Sentry context"""
        sentry_sdk.set_user(None)
        sentry_sdk.set_context("custom", {})


class AlertManager:
    """Manage alerts and notifications through Sentry and other channels"""
    
    @staticmethod
    def send_alert(
        title: str,
        message: str,
        severity: AlertSeverity,
        context: Optional[Dict[str, Any]] = None,
        notify_channels: Optional[List[str]] = None
    ):
        """Send alert through Sentry and other configured channels"""
        
        # Determine Sentry level based on severity
        sentry_level = {
            AlertSeverity.LOW: "info",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "error",
            AlertSeverity.CRITICAL: "fatal"
        }.get(severity, "error")
        
        # Create alert context
        alert_context = {
            "alert_title": title,
            "alert_severity": severity.value,
            "alert_message": message,
            **(context or {})
        }
        
        # Send to Sentry
        with sentry_sdk.push_scope() as scope:
            scope.level = sentry_level
            scope.set_tag("alert_severity", severity.value)
            scope.set_tag("alert_type", "manual_alert")
            
            for key, value in alert_context.items():
                scope.set_extra(key, value)
                
            # Use fingerprint to group similar alerts
            fingerprint = [title, severity.value]
            scope.fingerprint = fingerprint
            
            sentry_sdk.capture_message(f"Alert: {title} - {message}", level=sentry_level)
            
        # Log the alert
        logger.warning(
            f"Alert sent: {title}",
            severity=severity.value,
            message=message,
            context=context
        )
        
        # Send to other channels if configured
        if notify_channels:
            for channel in notify_channels:
                AlertManager._send_to_channel(channel, title, message, severity, context)
                
    @staticmethod
    def _send_to_channel(
        channel: str,
        title: str,
        message: str,
        severity: AlertSeverity,
        context: Optional[Dict[str, Any]] = None
    ):
        """Send alert to specific channel (implement as needed)"""
        # This is where you'd integrate with Slack, email, PagerDuty, etc.
        logger.info(f"Would send alert to {channel}", title=title)


def monitor_performance(operation_name: str, capture_args: bool = False):
    """
    Decorator to monitor function performance with Sentry
    
    Args:
        operation_name: Name of the operation being monitored
        capture_args: Whether to capture function arguments in span
        
    Example:
        @monitor_performance("external_api.polygon")
        async def fetch_market_data(symbol: str):
            return await polygon_service.get_data(symbol)
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op=operation_name, name=func.__name__) as transaction:
                # Add function context
                transaction.set_tag("function", f"{func.__module__}.{func.__name__}")
                
                # Capture arguments if requested
                if capture_args and (args or kwargs):
                    transaction.set_data("args", str(args[:3]))  # Limit to first 3 args
                    transaction.set_data("kwargs", str(list(kwargs.keys())))
                    
                # Start main span
                with sentry_sdk.start_span(op=f"{operation_name}.execute") as span:
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        span.set_tag("success", True)
                        return result
                    except Exception as e:
                        span.set_tag("success", False)
                        span.set_tag("error", type(e).__name__)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_data("duration_ms", round(duration * 1000, 2))
                        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op=operation_name, name=func.__name__) as transaction:
                transaction.set_tag("function", f"{func.__module__}.{func.__name__}")
                
                if capture_args and (args or kwargs):
                    transaction.set_data("args", str(args[:3]))
                    transaction.set_data("kwargs", str(list(kwargs.keys())))
                    
                with sentry_sdk.start_span(op=f"{operation_name}.execute") as span:
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        span.set_tag("success", True)
                        return result
                    except Exception as e:
                        span.set_tag("success", False)
                        span.set_tag("error", type(e).__name__)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_data("duration_ms", round(duration * 1000, 2))
                        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def capture_errors(
    reraise: bool = True,
    level: str = "error",
    fingerprint: Optional[List[str]] = None
):
    """
    Decorator to automatically capture exceptions
    
    Args:
        reraise: Whether to reraise the exception after capturing
        level: Sentry level for the error
        fingerprint: Custom fingerprint for error grouping
        
    Example:
        @capture_errors(level="warning")
        async def risky_operation():
            # Code that might fail
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ErrorMonitoring.capture_exception(
                    e,
                    context={
                        "function": f"{func.__module__}.{func.__name__}",
                        "args": str(args[:3]) if args else None,
                        "kwargs": str(list(kwargs.keys())) if kwargs else None
                    },
                    level=level,
                    fingerprint=fingerprint
                )
                if reraise:
                    raise
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorMonitoring.capture_exception(
                    e,
                    context={
                        "function": f"{func.__module__}.{func.__name__}",
                        "args": str(args[:3]) if args else None,
                        "kwargs": str(list(kwargs.keys())) if kwargs else None
                    },
                    level=level,
                    fingerprint=fingerprint
                )
                if reraise:
                    raise
                    
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Import logging to make LoggingIntegration work
import logging