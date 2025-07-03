"""Enhanced logging utilities for debugging and monitoring."""

import time
import uuid
import functools
import asyncio
from typing import Any, Dict, Optional, Callable
from contextvars import ContextVar

import logfire

# Context variable to track request ID across async operations
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class StructuredLogger:
    """Structured logging with consistent fields and request tracking."""

    @staticmethod
    def set_request_id(request_id: str = None) -> str:
        """Set request ID for current context."""
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]
        request_id_var.set(request_id)
        return request_id

    @staticmethod
    def get_request_id() -> str:
        """Get current request ID."""
        return request_id_var.get()

    @staticmethod
    def _add_context(data: Dict[str, Any]) -> Dict[str, Any]:
        """Add standard context fields to log data."""
        request_id = request_id_var.get()
        if request_id:
            data["request_id"] = request_id
        data["timestamp"] = time.time()
        return data

    @classmethod
    def debug(cls, message: str, **kwargs):
        """Debug level logging."""
        logfire.debug(message, **cls._add_context(kwargs))

    @classmethod
    def info(cls, message: str, **kwargs):
        """Info level logging."""
        logfire.info(message, **cls._add_context(kwargs))

    @classmethod
    def warning(cls, message: str, **kwargs):
        """Warning level logging."""
        logfire.warning(message, **cls._add_context(kwargs))

    @classmethod
    def error(cls, message: str, **kwargs):
        """Error level logging."""
        logfire.error(message, **cls._add_context(kwargs))


def log_function_call(
    log_args: bool = True,
    log_result: bool = False,
    log_timing: bool = True,
    log_level: str = "debug",
):
    """Decorator to log function calls with timing and parameters."""

    def decorator(func: Callable) -> Callable:
        function_name = f"{func.__module__}.{func.__qualname__}"
        
        if asyncio.iscoroutinefunction(func):
            return _create_async_wrapper(func, function_name, log_args, log_result, log_timing, log_level)
        else:
            return _create_sync_wrapper(func, function_name, log_args, log_result, log_timing, log_level)

    return decorator


def _create_async_wrapper(func: Callable, function_name: str, log_args: bool, log_result: bool, log_timing: bool, log_level: str):
    """Create async wrapper for function logging."""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        _log_function_start(function_name, args, kwargs, log_args, log_level)

        try:
            result = await func(*args, **kwargs)
            _log_function_success(function_name, result, start_time, log_result, log_timing, log_level)
            return result
        except Exception as e:
            _log_function_error(function_name, e, start_time)
            raise

    return async_wrapper


def _create_sync_wrapper(func: Callable, function_name: str, log_args: bool, log_result: bool, log_timing: bool, log_level: str):
    """Create sync wrapper for function logging."""
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        _log_function_start(function_name, args, kwargs, log_args, log_level)

        try:
            result = func(*args, **kwargs)
            _log_function_success(function_name, result, start_time, log_result, log_timing, log_level)
            return result
        except Exception as e:
            _log_function_error(function_name, e, start_time)
            raise

    return sync_wrapper


def _log_function_start(function_name: str, args: tuple, kwargs: dict, log_args: bool, log_level: str):
    """Log function start with sanitized arguments."""
    log_data = {"function": function_name, "operation": "function_call_start"}

    if log_args:
        log_data.update(_sanitize_function_args(args, kwargs))

    getattr(StructuredLogger, log_level)(f"Starting {function_name}", **log_data)


def _sanitize_function_args(args: tuple, kwargs: dict) -> dict:
    """Sanitize function arguments for safe logging."""
    safe_args = []
    for arg in args:
        if hasattr(arg, "__dict__"):
            safe_args.append(f"<{type(arg).__name__}>")
        else:
            safe_args.append(str(arg)[:100])

    safe_kwargs = {}
    for k, v in kwargs.items():
        if _is_sensitive_key(k):
            safe_kwargs[k] = "<REDACTED>"
        else:
            safe_kwargs[k] = str(v)[:100] if isinstance(v, str) else v

    return {"args": safe_args, "kwargs": safe_kwargs}


def _is_sensitive_key(key: str) -> bool:
    """Check if a key contains sensitive information."""
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in ["key", "token", "secret"])


def _log_function_success(function_name: str, result, start_time: float, log_result: bool, log_timing: bool, log_level: str):
    """Log successful function completion."""
    execution_time = time.time() - start_time
    result_log_data = {
        "function": function_name,
        "operation": "function_call_success",
        "execution_time_ms": round(execution_time * 1000, 2),
    }

    if log_result:
        _add_result_info(result_log_data, result)

    if log_timing:
        _add_timing_info(result_log_data, execution_time)

    getattr(StructuredLogger, log_level)(f"Completed {function_name}", **result_log_data)


def _add_result_info(log_data: dict, result) -> None:
    """Add result information to log data."""
    if hasattr(result, "__dict__"):
        log_data["result_type"] = type(result).__name__
    else:
        log_data["result"] = str(result)[:200]


def _add_timing_info(log_data: dict, execution_time: float) -> None:
    """Add timing information to log data."""
    log_data["performance"] = {
        "execution_time_ms": round(execution_time * 1000, 2),
        "is_slow": execution_time > 1.0,
    }


def _log_function_error(function_name: str, error: Exception, start_time: float):
    """Log function error with details."""
    execution_time = time.time() - start_time
    error_log_data = {
        "function": function_name,
        "operation": "function_call_error",
        "execution_time_ms": round(execution_time * 1000, 2),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_args": getattr(error, "args", []),
    }

    StructuredLogger.error(f"Failed {function_name}", **error_log_data)


class APICallLogger:
    """Specialized logging for external API calls."""

    @staticmethod
    def log_request(service: str, endpoint: str, method: str = "GET", **kwargs):
        """Log outgoing API request."""
        StructuredLogger.info(
            f"API Request: {service}",
            operation="api_request_start",
            service=service,
            endpoint=endpoint,
            method=method,
            **kwargs,
        )

    @staticmethod
    def log_response(
        service: str,
        endpoint: str,
        status_code: Optional[int] = None,
        response_size: Optional[int] = None,
        execution_time_ms: Optional[float] = None,
        **kwargs,
    ):
        """Log API response."""
        log_data = {
            "operation": "api_request_success",
            "service": service,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_size_bytes": response_size,
            "execution_time_ms": execution_time_ms,
        }
        log_data.update(kwargs)

        if execution_time_ms and execution_time_ms > 2000:
            StructuredLogger.warning(f"Slow API Response: {service}", **log_data)
        else:
            StructuredLogger.info(f"API Response: {service}", **log_data)

    @staticmethod
    def log_error(service: str, endpoint: str, error: Exception, **kwargs):
        """Log API error."""
        StructuredLogger.error(
            f"API Error: {service}",
            operation="api_request_error",
            service=service,
            endpoint=endpoint,
            error_type=type(error).__name__,
            error_message=str(error),
            **kwargs,
        )


class ConfigLogger:
    """Log application configuration state."""

    @staticmethod
    def log_startup_config(**config_data):
        """Log configuration at startup."""
        # Redact sensitive values
        safe_config = {}
        for key, value in config_data.items():
            if any(
                sensitive in key.lower()
                for sensitive in ["key", "token", "secret", "password"]
            ):
                safe_config[key] = "<REDACTED>" if value else None
            else:
                safe_config[key] = value

        StructuredLogger.info(
            "Application Configuration", operation="startup_config", config=safe_config
        )

    @staticmethod
    def log_feature_flags(**flags):
        """Log feature flag states."""
        StructuredLogger.info("Feature Flags", operation="feature_flags", flags=flags)


class DataFlowLogger:
    """Log data transformations and flow."""

    @staticmethod
    def log_data_transformation(
        stage: str,
        input_count: int,
        output_count: int,
        transformation_type: str,
        **kwargs,
    ):
        """Log data transformation step."""
        StructuredLogger.info(
            f"Data Transformation: {stage}",
            operation="data_transformation",
            stage=stage,
            input_count=input_count,
            output_count=output_count,
            transformation_type=transformation_type,
            **kwargs,
        )

    @staticmethod
    def log_data_validation(
        entity_type: str, count: int, validation_errors: list = None
    ):
        """Log data validation results."""
        log_data = {
            "operation": "data_validation",
            "entity_type": entity_type,
            "count": count,
            "is_valid": not validation_errors,
        }

        if validation_errors:
            log_data["validation_errors"] = validation_errors[:10]  # Limit error list
            StructuredLogger.warning(
                f"Data Validation Issues: {entity_type}", **log_data
            )
        else:
            StructuredLogger.debug(f"Data Validation Passed: {entity_type}", **log_data)


# Convenience instance
logger = StructuredLogger()
