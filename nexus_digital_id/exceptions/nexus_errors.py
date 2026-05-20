"""
Nexus Digital ID - Custom Exception Definitions

A structured exception hierarchy providing granular error categorisation
for the identity management ecosystem.

Error Code Prefixes:
- NXS-1xx: Identity Vault Errors
- NXS-2xx: Status Management Errors  
- NXS-3xx: Authorisation Errors
- NXS-4xx: Validation Errors
- NXS-5xx: Business Rule Errors
- NXS-6xx: Audit/System Errors
"""

from enum import Enum
from typing import Optional, List, Dict, Any


class ErrorCategory(Enum):
    """Classification of error types for consistent response handling."""
    VALIDATION = "VALIDATION"
    AUTHORISATION = "AUTHORISATION"
    NOT_FOUND = "NOT_FOUND"
    BUSINESS_RULE = "BUSINESS_RULE"
    SYSTEM = "SYSTEM"
    CONFLICT = "CONFLICT"


class NexusBaseException(Exception):
    """
    Foundation exception for all Nexus Digital ID errors.
    
    Provides structured error information without exposing
    internal system details to external consumers.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.category = category
        self.details = details or {}
        super().__init__(self.message)
    
    def to_response_dict(self) -> Dict[str, Any]:
        """Convert exception to safe external response format."""
        return {
            "success": False,
            "error_code": self.error_code,
            "error_category": self.category.value,
            "message": self.message,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.error_code}, message={self.message})"


# ============================================================================
# Identity Vault Errors (NXS-1xx)
# ============================================================================

class IdentityVaultError(NexusBaseException):
    """Base exception for identity storage operations."""
    
    def __init__(self, message: str, error_code: str = "NXS-100", 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, ErrorCategory.SYSTEM, details)


class IdentityNotFoundError(NexusBaseException):
    """Raised when a requested Digital ID does not exist in the vault."""
    
    def __init__(self, identity_ref: str):
        super().__init__(
            message=f"Digital Identity with reference '{identity_ref}' was not found",
            error_code="NXS-101",
            category=ErrorCategory.NOT_FOUND,
            details={"identity_reference": identity_ref}
        )
        self.identity_ref = identity_ref


class DuplicateIdentityError(NexusBaseException):
    """Raised when attempting to create an identity that already exists."""
    
    def __init__(self, identity_ref: str, existing_ref: Optional[str] = None):
        super().__init__(
            message="An identity with matching attributes already exists",
            error_code="NXS-102",
            category=ErrorCategory.CONFLICT,
            details={"attempted_reference": identity_ref}
        )
        self.identity_ref = identity_ref
        self.existing_ref = existing_ref


class ImmutableAttributeViolation(NexusBaseException):
    """Raised when attempting to modify a protected attribute."""
    
    def __init__(self, attribute_name: str):
        super().__init__(
            message=f"Attribute '{attribute_name}' is immutable and cannot be modified after creation",
            error_code="NXS-103",
            category=ErrorCategory.BUSINESS_RULE,
            details={"attribute": attribute_name}
        )
        self.attribute_name = attribute_name


# ============================================================================
# Status Management Errors (NXS-2xx)
# ============================================================================

class RevokedIdentityError(NexusBaseException):
    """Raised when attempting operations on a permanently revoked identity."""
    
    def __init__(self, identity_ref: str, attempted_operation: str):
        super().__init__(
            message=f"Cannot perform '{attempted_operation}' on revoked identity",
            error_code="NXS-201",
            category=ErrorCategory.BUSINESS_RULE,
            details={
                "identity_reference": identity_ref,
                "attempted_operation": attempted_operation
            }
        )
        self.identity_ref = identity_ref
        self.attempted_operation = attempted_operation


class InvalidStatusTransitionError(NexusBaseException):
    """Raised when a status change violates transition rules."""
    
    def __init__(self, current_status: str, requested_status: str, identity_ref: str):
        super().__init__(
            message=f"Cannot transition from '{current_status}' to '{requested_status}'",
            error_code="NXS-202",
            category=ErrorCategory.BUSINESS_RULE,
            details={
                "current_status": current_status,
                "requested_status": requested_status,
                "identity_reference": identity_ref
            }
        )
        self.current_status = current_status
        self.requested_status = requested_status
        self.identity_ref = identity_ref


# ============================================================================
# Authorisation Errors (NXS-3xx)
# ============================================================================

class AuthorisationDeniedError(NexusBaseException):
    """Base exception for authorisation failures."""
    
    def __init__(self, message: str = "Authorisation denied for this operation",
                 error_code: str = "NXS-300"):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.AUTHORISATION
        )


class UnregisteredOrganisationError(AuthorisationDeniedError):
    """Raised when an unregistered organisation attempts an operation."""
    
    def __init__(self):
        # Deliberately vague message to avoid information disclosure
        super().__init__(
            message="Authorisation denied for this operation",
            error_code="NXS-301"
        )


class InsufficientAccessTierError(AuthorisationDeniedError):
    """Raised when organisation lacks required access level."""
    
    def __init__(self):
        # Deliberately vague message to avoid information disclosure
        super().__init__(
            message="Authorisation denied for this operation",
            error_code="NXS-302"
        )


# ============================================================================
# Validation Errors (NXS-4xx)
# ============================================================================

class ValidationFailureError(NexusBaseException):
    """Base exception for request validation failures."""
    
    def __init__(self, message: str, failures: Optional[List[str]] = None):
        super().__init__(
            message=message,
            error_code="NXS-400",
            category=ErrorCategory.VALIDATION,
            details={"validation_failures": failures or []}
        )
        self.failures = failures or []


class MissingFieldError(ValidationFailureError):
    """Raised when required fields are absent from a request."""
    
    def __init__(self, missing_fields: List[str]):
        fields_str = ", ".join(missing_fields)
        super().__init__(
            message=f"Required fields missing: {fields_str}",
            failures=[f"Missing: {field}" for field in missing_fields]
        )
        self.error_code = "NXS-401"
        self.missing_fields = missing_fields


class InvalidFieldFormatError(ValidationFailureError):
    """Raised when field values do not conform to expected formats."""
    
    def __init__(self, field_errors: Dict[str, str]):
        errors_list = [f"{field}: {reason}" for field, reason in field_errors.items()]
        super().__init__(
            message="One or more fields contain invalid values",
            failures=errors_list
        )
        self.error_code = "NXS-402"
        self.field_errors = field_errors


class InvalidReportingPeriodError(ValidationFailureError):
    """Raised when a reporting period specification is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid reporting period: {reason}",
            failures=[reason]
        )
        self.error_code = "NXS-403"
        self.reason = reason


# ============================================================================
# Business Rule Errors (NXS-5xx)
# ============================================================================

class BusinessRuleViolationError(NexusBaseException):
    """Raised when an operation violates a business rule."""
    
    def __init__(self, rule_name: str, description: str):
        super().__init__(
            message=f"Business rule violation: {description}",
            error_code="NXS-500",
            category=ErrorCategory.BUSINESS_RULE,
            details={"rule": rule_name}
        )
        self.rule_name = rule_name
        self.description = description


# ============================================================================
# System/Audit Errors (NXS-6xx)
# ============================================================================

class AuditLoggingFailureError(NexusBaseException):
    """Raised when audit logging fails, preventing operation completion."""
    
    def __init__(self, operation: str):
        super().__init__(
            message="Operation could not be completed due to audit logging failure",
            error_code="NXS-601",
            category=ErrorCategory.SYSTEM,
            details={"operation": operation}
        )
        self.operation = operation
