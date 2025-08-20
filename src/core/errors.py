"""Error classification and tracking for the setup agent."""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class ErrorType(Enum):
    """Standardized error types for classification"""
    # Language/Platform errors
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    LANGUAGE_NOT_FOUND = "language_not_found"
    
    # Installation errors
    INSTALLATION_FAILED = "installation_failed"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    VERSION_MISMATCH = "version_mismatch"
    PACKAGE_NOT_FOUND = "package_not_found"
    
    # System errors
    PERMISSION_DENIED = "permission_denied"
    INSUFFICIENT_SPACE = "insufficient_space"
    PATH_NOT_FOUND = "path_not_found"
    
    # Network errors
    NETWORK_ERROR = "network_error"
    DOWNLOAD_FAILED = "download_failed"
    REGISTRY_UNREACHABLE = "registry_unreachable"
    
    # Execution errors
    TIMEOUT = "timeout"
    COMMAND_FAILED = "command_failed"
    INVALID_CONFIG = "invalid_config"
    
    # Unknown
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # Stops entire workflow
    HIGH = "high"          # Stops current language/component
    MEDIUM = "medium"      # Can retry or work around
    LOW = "low"            # Warning, doesn't stop execution


class SetupError:
    """Structured error information"""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        severity: ErrorSeverity,
        agent: str,
        language: Optional[str] = None,
        command: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        self.message = message
        self.severity = severity
        self.agent = agent
        self.language = language
        self.command = command
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_type': self.error_type.value,
            'message': self.message,
            'severity': self.severity.value,
            'agent': self.agent,
            'language': self.language,
            'command': self.command,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        agent: str,
        language: Optional[str] = None,
        command: Optional[str] = None
    ) -> 'SetupError':
        """Create SetupError from an exception"""
        
        # Classify error based on exception message
        error_type = cls._classify_exception(exception)
        severity = cls._determine_severity(error_type)
        
        return cls(
            error_type=error_type,
            message=str(exception),
            severity=severity,
            agent=agent,
            language=language,
            command=command,
            details={'exception_type': type(exception).__name__}
        )
    
    @staticmethod
    def _classify_exception(exception: Exception) -> ErrorType:
        """Classify exception into error type"""
        error_msg = str(exception).lower()
        
        # Network related
        if any(word in error_msg for word in ['network', 'connection', 'download', 'fetch']):
            return ErrorType.NETWORK_ERROR
        
        # Permission related
        if any(word in error_msg for word in ['permission', 'access denied', 'eacces', 'unauthorized']):
            return ErrorType.PERMISSION_DENIED
        
        # Timeout
        if 'timeout' in error_msg:
            return ErrorType.TIMEOUT
        
        # Package/dependency related
        if any(word in error_msg for word in ['not found', 'cannot find', 'missing']):
            return ErrorType.PACKAGE_NOT_FOUND
        
        # Installation
        if any(word in error_msg for word in ['install', 'setup']):
            return ErrorType.INSTALLATION_FAILED
        
        return ErrorType.UNKNOWN
    
    @staticmethod
    def _determine_severity(error_type: ErrorType) -> ErrorSeverity:
        """Determine severity based on error type"""
        severity_map = {
            ErrorType.UNSUPPORTED_LANGUAGE: ErrorSeverity.CRITICAL,
            ErrorType.PERMISSION_DENIED: ErrorSeverity.HIGH,
            ErrorType.INSTALLATION_FAILED: ErrorSeverity.HIGH,
            ErrorType.NETWORK_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorType.PACKAGE_NOT_FOUND: ErrorSeverity.MEDIUM,
            ErrorType.VERSION_MISMATCH: ErrorSeverity.LOW,
            ErrorType.UNKNOWN: ErrorSeverity.MEDIUM
        }
        return severity_map.get(error_type, ErrorSeverity.MEDIUM)


class ErrorTracker:
    """Track and aggregate errors during setup"""
    
    def __init__(self):
        self.errors: List[SetupError] = []
    
    def add_error(self, error: SetupError):
        """Add an error to the tracker"""
        self.errors.append(error)
    
    def get_errors_by_type(self, error_type: ErrorType) -> List[SetupError]:
        """Get all errors of a specific type"""
        return [e for e in self.errors if e.error_type == error_type]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[SetupError]:
        """Get all errors of a specific severity"""
        return [e for e in self.errors if e.severity == severity]
    
    def get_errors_by_language(self, language: str) -> List[SetupError]:
        """Get all errors for a specific language"""
        return [e for e in self.errors if e.language == language]
    
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors"""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        type_counts = {}
        severity_counts = {}
        language_counts = {}
        
        for error in self.errors:
            # Count by type
            type_counts[error.error_type.value] = type_counts.get(error.error_type.value, 0) + 1
            
            # Count by severity
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            
            # Count by language
            if error.language:
                language_counts[error.language] = language_counts.get(error.language, 0) + 1
        
        return {
            'total_errors': len(self.errors),
            'by_type': type_counts,
            'by_severity': severity_counts,
            'by_language': language_counts,
            'has_critical': self.has_critical_errors()
        }
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert all errors to list of dictionaries"""
        return [error.to_dict() for error in self.errors]