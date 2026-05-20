"""
Nexus Digital ID - Core Module

Contains the fundamental data structures and services for identity management:
- IdentityVault: Storage and retrieval of Digital ID records
- StatusSentinel: Status lifecycle management
- AttributeKeeper: Attribute modification handling
"""

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityRecord,
    ImmutableAttributes,
    ModifiableAttributes,
    StatusHistoryEntry,
    TemporaryRestriction,
)
from nexus_digital_id.core.status_sentinel import StatusSentinel, IdentityStatus
from nexus_digital_id.core.attribute_keeper import AttributeKeeper

__all__ = [
    "DigitalIdentityVault",
    "IdentityRecord",
    "ImmutableAttributes",
    "ModifiableAttributes",
    "StatusHistoryEntry",
    "TemporaryRestriction",
    "StatusSentinel",
    "IdentityStatus",
    "AttributeKeeper",
]
