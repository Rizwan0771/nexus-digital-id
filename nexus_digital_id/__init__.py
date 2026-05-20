"""
Nexus Digital Identity Management System

A federated identity management platform enabling central authority control
with tiered access for consuming organisations.

Author: Hussarim
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Hussarim"

from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityRecord
from nexus_digital_id.core.status_sentinel import StatusSentinel, IdentityStatus
from nexus_digital_id.authority.central_command import CentralCommand
from nexus_digital_id.authority.org_registry import OrganisationRegistry, AccessTier

__all__ = [
    "DigitalIdentityVault",
    "IdentityRecord", 
    "StatusSentinel",
    "IdentityStatus",
    "CentralCommand",
    "OrganisationRegistry",
    "AccessTier",
]
