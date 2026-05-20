"""
Nexus Digital ID - Organisation Registry

Manages the registration and access control of consuming organisations
within the Digital ID ecosystem.

Access Tiers:
- BASIC: Simple validity checks only (employers, banks)
- STANDARD: Validity plus limited attributes (local authorities, welfare)
- ENHANCED: Full verification with history (tax, DVLA, immigration)
"""

from enum import Enum
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime


class AccessTier(Enum):
    """
    Tiered access levels for consuming organisations.
    
    Each tier defines what operations and data an organisation
    can access through the verification services.
    """
    BASIC = "BASIC"         # Validity check only, no attributes
    STANDARD = "STANDARD"   # Validity + limited non-sensitive attributes
    ENHANCED = "ENHANCED"   # Full verification with history access


class OrganisationType(Enum):
    """
    Classification of organisation types in the ecosystem.
    
    Used for routing verification requests to appropriate handlers
    and applying organisation-specific business rules.
    """
    CENTRAL_AUTHORITY = "CENTRAL_AUTHORITY"
    TAX_AUTHORITY = "TAX_AUTHORITY"
    DRIVING_LICENCE_AUTHORITY = "DRIVING_LICENCE_AUTHORITY"
    WELFARE_SERVICES = "WELFARE_SERVICES"
    IMMIGRATION = "IMMIGRATION"
    LOCAL_AUTHORITY = "LOCAL_AUTHORITY"
    EMPLOYER = "EMPLOYER"
    BANK = "BANK"
    OTHER = "OTHER"


# Define which organisation types get which access tier by default
_DEFAULT_ACCESS_TIERS: Dict[OrganisationType, AccessTier] = {
    OrganisationType.CENTRAL_AUTHORITY: AccessTier.ENHANCED,
    OrganisationType.TAX_AUTHORITY: AccessTier.ENHANCED,
    OrganisationType.DRIVING_LICENCE_AUTHORITY: AccessTier.ENHANCED,
    OrganisationType.IMMIGRATION: AccessTier.ENHANCED,
    OrganisationType.WELFARE_SERVICES: AccessTier.STANDARD,
    OrganisationType.LOCAL_AUTHORITY: AccessTier.STANDARD,
    OrganisationType.EMPLOYER: AccessTier.BASIC,
    OrganisationType.BANK: AccessTier.BASIC,
    OrganisationType.OTHER: AccessTier.BASIC,
}


@dataclass
class RegisteredOrganisation:
    """
    Record of a registered consuming organisation.
    
    Contains all information needed to authorise and route
    requests from the organisation.
    """
    org_id: str
    org_name: str
    org_type: OrganisationType
    access_tier: AccessTier
    registration_timestamp: datetime
    is_active: bool = True
    contact_email: Optional[str] = None
    permitted_operations: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Set default permitted operations based on access tier."""
        if not self.permitted_operations:
            self.permitted_operations = self._get_default_operations()
    
    def _get_default_operations(self) -> Set[str]:
        """Determine default operations based on access tier."""
        base_ops = {"verify_basic"}
        
        if self.access_tier == AccessTier.STANDARD:
            return base_ops | {"verify_standard", "retrieve_limited_attributes"}
        
        if self.access_tier == AccessTier.ENHANCED:
            return base_ops | {
                "verify_standard",
                "verify_enhanced",
                "retrieve_limited_attributes",
                "retrieve_full_attributes",
                "retrieve_status_history",
                "verify_tax_period",
                "verify_driving_eligibility",
            }
        
        return base_ops
    
    def can_perform_operation(self, operation: str) -> bool:
        """Check if organisation is permitted to perform an operation."""
        return self.is_active and operation in self.permitted_operations
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialisation."""
        return {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "org_type": self.org_type.value,
            "access_tier": self.access_tier.value,
            "registration_timestamp": self.registration_timestamp.isoformat(),
            "is_active": self.is_active,
            "contact_email": self.contact_email,
            "permitted_operations": list(self.permitted_operations),
        }


class OrganisationRegistry:
    """
    Central registry for managing consuming organisations.
    
    Handles registration, access tier assignment, and authorisation
    checks for all organisations interacting with the Digital ID platform.
    
    The Central Authority is pre-registered with full access and
    cannot be deactivated or removed.
    """
    
    # Reserved identifier for the Central Authority
    CENTRAL_AUTHORITY_ID = "NEXUS-CENTRAL-001"
    CENTRAL_AUTHORITY_NAME = "Nexus Central Authority"
    
    def __init__(self):
        """Initialise registry with Central Authority pre-registered."""
        self._organisations: Dict[str, RegisteredOrganisation] = {}
        self._name_index: Dict[str, str] = {}  # name -> org_id
        
        # Pre-register the Central Authority
        self._register_central_authority()
    
    def _register_central_authority(self) -> None:
        """Register the Central Authority with full privileges."""
        central_auth = RegisteredOrganisation(
            org_id=self.CENTRAL_AUTHORITY_ID,
            org_name=self.CENTRAL_AUTHORITY_NAME,
            org_type=OrganisationType.CENTRAL_AUTHORITY,
            access_tier=AccessTier.ENHANCED,
            registration_timestamp=datetime.utcnow(),
            is_active=True,
            permitted_operations={
                "create_identity",
                "update_identity",
                "change_status",
                "add_restriction",
                "remove_restriction",
                "verify_basic",
                "verify_standard",
                "verify_enhanced",
                "retrieve_limited_attributes",
                "retrieve_full_attributes",
                "retrieve_status_history",
                "verify_tax_period",
                "verify_driving_eligibility",
                "register_organisation",
                "deactivate_organisation",
                "view_audit_logs",
            },
        )
        self._organisations[central_auth.org_id] = central_auth
        self._name_index[central_auth.org_name.lower()] = central_auth.org_id
    
    def register_organisation(
        self,
        org_name: str,
        org_type: OrganisationType,
        access_tier: Optional[AccessTier] = None,
        contact_email: Optional[str] = None,
    ) -> RegisteredOrganisation:
        """
        Register a new consuming organisation.
        
        Args:
            org_name: Display name for the organisation
            org_type: Classification of organisation type
            access_tier: Access level (defaults based on org_type if not specified)
            contact_email: Optional contact email
            
        Returns:
            The newly registered organisation record
            
        Raises:
            ValueError: If organisation name already exists
        """
        # Check for duplicate name
        if org_name.lower() in self._name_index:
            raise ValueError(f"Organisation '{org_name}' is already registered")
        
        # Determine access tier
        if access_tier is None:
            access_tier = _DEFAULT_ACCESS_TIERS.get(org_type, AccessTier.BASIC)
        
        # Generate unique ID
        org_id = self._generate_org_id(org_type)
        
        organisation = RegisteredOrganisation(
            org_id=org_id,
            org_name=org_name,
            org_type=org_type,
            access_tier=access_tier,
            registration_timestamp=datetime.utcnow(),
            contact_email=contact_email,
        )
        
        self._organisations[org_id] = organisation
        self._name_index[org_name.lower()] = org_id
        
        return organisation
    
    def _generate_org_id(self, org_type: OrganisationType) -> str:
        """Generate a unique organisation identifier."""
        import uuid
        prefix_map = {
            OrganisationType.TAX_AUTHORITY: "TAX",
            OrganisationType.DRIVING_LICENCE_AUTHORITY: "DVLA",
            OrganisationType.WELFARE_SERVICES: "WELF",
            OrganisationType.IMMIGRATION: "IMMG",
            OrganisationType.LOCAL_AUTHORITY: "LOCL",
            OrganisationType.EMPLOYER: "EMPL",
            OrganisationType.BANK: "BANK",
            OrganisationType.OTHER: "OTHR",
        }
        prefix = prefix_map.get(org_type, "ORG")
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{unique_part}"
    
    def get_organisation(self, org_id: str) -> Optional[RegisteredOrganisation]:
        """Retrieve an organisation by ID."""
        return self._organisations.get(org_id)
    
    def get_organisation_by_name(self, org_name: str) -> Optional[RegisteredOrganisation]:
        """Retrieve an organisation by name (case-insensitive)."""
        org_id = self._name_index.get(org_name.lower())
        if org_id:
            return self._organisations.get(org_id)
        return None
    
    def is_registered(self, org_id: str) -> bool:
        """Check if an organisation ID is registered."""
        return org_id in self._organisations
    
    def is_active(self, org_id: str) -> bool:
        """Check if an organisation is registered and active."""
        org = self._organisations.get(org_id)
        return org is not None and org.is_active
    
    def deactivate_organisation(self, org_id: str) -> bool:
        """
        Deactivate an organisation (cannot deactivate Central Authority).
        
        Returns True if deactivated, False if not found or protected.
        """
        if org_id == self.CENTRAL_AUTHORITY_ID:
            return False
        
        org = self._organisations.get(org_id)
        if org:
            org.is_active = False
            return True
        return False
    
    def reactivate_organisation(self, org_id: str) -> bool:
        """
        Reactivate a previously deactivated organisation.
        
        Returns True if reactivated, False if not found.
        """
        org = self._organisations.get(org_id)
        if org:
            org.is_active = True
            return True
        return False
    
    def get_access_tier(self, org_id: str) -> Optional[AccessTier]:
        """Get the access tier for an organisation."""
        org = self._organisations.get(org_id)
        return org.access_tier if org else None
    
    def can_perform_operation(self, org_id: str, operation: str) -> bool:
        """Check if an organisation can perform a specific operation."""
        org = self._organisations.get(org_id)
        if not org:
            return False
        return org.can_perform_operation(operation)
    
    def is_central_authority(self, org_id: str) -> bool:
        """Check if the given ID is the Central Authority."""
        return org_id == self.CENTRAL_AUTHORITY_ID
    
    def get_all_organisations(self, include_inactive: bool = False) -> List[RegisteredOrganisation]:
        """
        Retrieve all registered organisations.
        
        Args:
            include_inactive: Whether to include deactivated organisations
        """
        if include_inactive:
            return list(self._organisations.values())
        return [org for org in self._organisations.values() if org.is_active]
    
    def count_organisations(self, include_inactive: bool = False) -> int:
        """Count registered organisations."""
        if include_inactive:
            return len(self._organisations)
        return sum(1 for org in self._organisations.values() if org.is_active)
