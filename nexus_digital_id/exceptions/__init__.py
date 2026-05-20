"""
Nexus Digital ID - Custom Exceptions Module

Provides a comprehensive hierarchy of exceptions for precise error handling
throughout the identity management system.
"""

from nexus_digital_id.exceptions.nexus_errors import (
    NexusBaseException,
    IdentityVaultError,
    IdentityNotFoundError,
    DuplicateIdentityError,
    ImmutableAttributeViolation,
    RevokedIdentityError,
    InvalidStatusTransitionError,
    AuthorisationDeniedError,
    UnregisteredOrganisationError,
    InsufficientAccessTierError,
    ValidationFailureError,
    MissingFieldError,
    InvalidFieldFormatError,
    BusinessRuleViolationError,
    AuditLoggingFailureError,
    InvalidReportingPeriodError,
)

__all__ = [
    "NexusBaseException",
    "IdentityVaultError",
    "IdentityNotFoundError",
    "DuplicateIdentityError",
    "ImmutableAttributeViolation",
    "RevokedIdentityError",
    "InvalidStatusTransitionError",
    "AuthorisationDeniedError",
    "UnregisteredOrganisationError",
    "InsufficientAccessTierError",
    "ValidationFailureError",
    "MissingFieldError",
    "InvalidFieldFormatError",
    "BusinessRuleViolationError",
    "AuditLoggingFailureError",
    "InvalidReportingPeriodError",
]
