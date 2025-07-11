"""Utility functions for service layer standardization."""

import functools
import time
from typing import Any, Callable, Dict, Optional, TypeVar
import logfire

# Type variables for generic decorators
T = TypeVar('T')


def with_error_handling(
    operation_name: str,
    service_name: str,
    log_level: str = "error",
    reraise: bool = True
):
    """Decorator for standardized error handling across services.
    
    Args:
        operation_name: Name of the operation for logging context
        service_name: Name of the service for logging context
        log_level: Log level for errors (default: "error")
        reraise: Whether to reraise exceptions (default: True)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "operation": operation_name,
                    "service": service_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__,
                }
                
                # Add positional arguments to context if they're primitive types
                for i, arg in enumerate(args[1:], 1):  # Skip self
                    if isinstance(arg, (str, int, float, bool)):
                        error_context[f"arg_{i}"] = arg
                
                # Add keyword arguments to context if they're primitive types
                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        error_context[key] = value
                
                if log_level == "error":
                    logfire.error(f"Service operation failed: {operation_name}", **error_context)
                elif log_level == "warning":
                    logfire.warning(f"Service operation failed: {operation_name}", **error_context)
                
                if reraise:
                    raise
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "operation": operation_name,
                    "service": service_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__,
                }
                
                # Add arguments to context
                for i, arg in enumerate(args[1:], 1):  # Skip self
                    if isinstance(arg, (str, int, float, bool)):
                        error_context[f"arg_{i}"] = arg
                
                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        error_context[key] = value
                
                if log_level == "error":
                    logfire.error(f"Service operation failed: {operation_name}", **error_context)
                elif log_level == "warning":
                    logfire.warning(f"Service operation failed: {operation_name}", **error_context)
                
                if reraise:
                    raise
                return None
        
        # Return appropriate wrapper based on whether function is async
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_performance_monitoring(operation_name: str, service_name: str):
    """Decorator for performance monitoring across services.
    
    Args:
        operation_name: Name of the operation for logging context
        service_name: Name of the service for logging context
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            try:
                with logfire.span(f"{service_name}_{operation_name}"):
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    logfire.info(
                        f"Service operation completed: {operation_name}",
                        service=service_name,
                        operation=operation_name,
                        duration_ms=duration * 1000,
                        function=func.__name__
                    )
                    return result
            except Exception as e:
                duration = time.time() - start_time
                logfire.error(
                    f"Service operation failed: {operation_name}",
                    service=service_name,
                    operation=operation_name,
                    duration_ms=duration * 1000,
                    error=str(e),
                    function=func.__name__
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            try:
                with logfire.span(f"{service_name}_{operation_name}"):
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    logfire.info(
                        f"Service operation completed: {operation_name}",
                        service=service_name,
                        operation=operation_name,
                        duration_ms=duration * 1000,
                        function=func.__name__
                    )
                    return result
            except Exception as e:
                duration = time.time() - start_time
                logfire.error(
                    f"Service operation failed: {operation_name}",
                    service=service_name,
                    operation=operation_name,
                    duration_ms=duration * 1000,
                    error=str(e),
                    function=func.__name__
                )
                raise
        
        # Return appropriate wrapper based on whether function is async
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_service_parameters(**validators):
    """Decorator for standardized parameter validation across services.
    
    Args:
        **validators: Mapping of parameter names to validation functions
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Get function signature for parameter mapping
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameters
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    param_value = bound_args.arguments[param_name]
                    try:
                        validator(param_value)
                    except (AssertionError, ValueError, TypeError) as e:
                        error_msg = f"Parameter validation failed for '{param_name}': {str(e)}"
                        logfire.error(
                            "Service parameter validation failed",
                            function=func.__name__,
                            parameter=param_name,
                            value=str(param_value),
                            error=str(e)
                        )
                        raise ValueError(error_msg) from e
            
            return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Get function signature for parameter mapping
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameters
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    param_value = bound_args.arguments[param_name]
                    try:
                        validator(param_value)
                    except (AssertionError, ValueError, TypeError) as e:
                        error_msg = f"Parameter validation failed for '{param_name}': {str(e)}"
                        logfire.error(
                            "Service parameter validation failed",
                            function=func.__name__,
                            parameter=param_name,
                            value=str(param_value),
                            error=str(e)
                        )
                        raise ValueError(error_msg) from e
            
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on whether function is async
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
            return async_wrapper
        else:
            return wrapper
    
    return decorator


class ServiceValidators:
    """Common validation functions for service parameters."""
    
    @staticmethod
    def non_empty_string(value: Any) -> None:
        """Validate that value is a non-empty string."""
        assert value is not None, "Value cannot be None"
        assert isinstance(value, str), f"Expected string, got {type(value)}"
        assert value.strip(), "String cannot be empty or whitespace only"
    
    @staticmethod
    def positive_integer(value: Any) -> None:
        """Validate that value is a positive integer."""
        assert value is not None, "Value cannot be None"
        assert isinstance(value, int), f"Expected integer, got {type(value)}"
        assert value > 0, f"Expected positive integer, got {value}"
    
    @staticmethod
    def non_negative_integer(value: Any) -> None:
        """Validate that value is a non-negative integer."""
        assert value is not None, "Value cannot be None"
        assert isinstance(value, int), f"Expected integer, got {type(value)}"
        assert value >= 0, f"Expected non-negative integer, got {value}"
    
    @staticmethod
    def ethereum_address(value: Any) -> None:
        """Validate that value is a valid Ethereum address."""
        ServiceValidators.non_empty_string(value)
        assert value.startswith("0x"), "Ethereum address must start with '0x'"
        assert len(value) == 42, f"Ethereum address must be 42 characters, got {len(value)}"
        try:
            int(value[2:], 16)
        except ValueError:
            raise AssertionError("Ethereum address must contain valid hexadecimal characters")
    
    @staticmethod
    def confidence_score(value: Any) -> None:
        """Validate that value is a confidence score between 0 and 1."""
        assert value is not None, "Confidence score cannot be None"
        assert isinstance(value, (int, float)), f"Expected number, got {type(value)}"
        assert 0.0 <= value <= 1.0, f"Confidence score must be between 0 and 1, got {value}"
    
    @staticmethod
    def list_of_strings(value: Any) -> None:
        """Validate that value is a list of non-empty strings."""
        assert value is not None, "List cannot be None"
        assert isinstance(value, list), f"Expected list, got {type(value)}"
        assert len(value) > 0, "List cannot be empty"
        for i, item in enumerate(value):
            assert isinstance(item, str), f"List item {i} must be string, got {type(item)}"
            assert item.strip(), f"List item {i} cannot be empty or whitespace only"


def create_service_response(
    success: bool,
    data: Optional[Any] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create standardized service response format.
    
    Args:
        success: Whether the operation was successful
        data: Response data if successful
        error: Error message if failed
        metadata: Additional metadata about the operation
    
    Returns:
        Standardized response dictionary
    """
    response = {
        "success": success,
        "timestamp": time.time(),
    }
    
    if success:
        response["data"] = data
    else:
        response["error"] = error or "Unknown error occurred"
    
    if metadata:
        response["metadata"] = metadata
    
    return response


def log_service_operation(
    service_name: str,
    operation: str,
    status: str,
    **kwargs
) -> None:
    """Log service operations with standardized format.
    
    Args:
        service_name: Name of the service
        operation: Name of the operation
        status: Status of the operation (success, error, warning)
        **kwargs: Additional context data
    """
    log_data = {
        "service": service_name,
        "operation": operation,
        "status": status,
        **kwargs
    }
    
    if status == "success":
        logfire.info(f"Service operation: {service_name}.{operation}", **log_data)
    elif status == "error":
        logfire.error(f"Service operation failed: {service_name}.{operation}", **log_data)
    elif status == "warning":
        logfire.warning(f"Service operation warning: {service_name}.{operation}", **log_data)
    else:
        logfire.info(f"Service operation: {service_name}.{operation}", **log_data)