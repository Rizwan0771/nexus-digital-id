"""
Nexus Digital ID - Authority Module

Contains components for central authority operations and
organisation management:
- CentralCommand: Main interface for identity management operations
- OrganisationRegistry: Registration and access control for consuming orgs
"""

from nexus_digital_id.authority.central_command import CentralCommand
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    AccessTier,
    RegisteredOrganisation,
    OrganisationType,
)

__all__ = [
    "CentralCommand",
    "OrganisationRegistry",
    "AccessTier",
    "RegisteredOrganisation",
    "OrganisationType",
]
