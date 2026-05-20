"""
Nexus Digital ID - Central Command

The primary interface for Central Authority operations on Digital Identities.
Orchestrates identity creation, attribute updates, and status management
while enforcing authorisation and business rules.

This is the main entry point for all identity management operations
and coordinates between the various subsystems.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityRecord,
    ImmutableAttributes,
    ModifiableAttributes,
    IdentityStatus,
    TemporaryRestriction,
)
from nexus_digital_id.core.status_sentinel import StatusSentinel
from nexus_digital_id.core.attribute_keeper import AttributeKeeper
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    AccessTier,
    OrganisationType,
)
from nexus_digital_id.exceptions import (
    AuthorisationDeniedError,
    IdentityNotFoundError,
    RevokedIdentityError,
    ValidationFailureError,
)


class CentralCommand:
    """
    Command centre for Digital Identity management operations.
    
    Provides a unified interface for the Central Authority to:
    - Create new Digital Identities
    - Update modifiable attributes
    - Manage identity status (suspend, reactivate, revoke)
    - Add/remove temporary restrictions
    - Register consuming organisations
    
    All operations are authorised against the organisation registry
    and logged for audit purposes.
    """
    
    def __init__(
        self,
        identity_vault: Optional[DigitalIdentityVault] = None,
        org_registry: Optional[OrganisationRegistry] = None,
    ):
        """
        Initialise Central Command with required subsystems.
        
        Args:
            identity_vault: Storage for identity records (created if not provided)
            org_registry: Organisation registry (created if not provided)
        """
        self._vault = identity_vault or DigitalIdentityVault()
        self._registry = org_registry or OrganisationRegistry()
        self._status_sentinel = StatusSentinel(self._vault)
        self._attribute_keeper = AttributeKeeper(self._vault)
    
    @property
    def vault(self) -> DigitalIdentityVault:
        """Access to the identity vault."""
        return self._vault
    
    @property
    def registry(self) -> OrganisationRegistry:
        """Access to the organisation registry."""
        return self._registry
    
    @property
    def status_sentinel(self) -> StatusSentinel:
        """Access to the status management service."""
        return self._status_sentinel
    
    @property
    def attribute_keeper(self) -> AttributeKeeper:
        """Access to the attribute management service."""
        return self._attribute_keeper
    
    def _verify_central_authority(self, requesting_org_id: str) -> None:
        """
        Verify the requesting organisation is the Central Authority.
        
        Raises:
            AuthorisationDeniedError: If not the Central Authority
        """
        if not self._registry.is_central_authority(requesting_org_id):
            raise AuthorisationDeniedError(
                "Only the Central Authority can perform this operation"
            )
    
    def create_identity(
        self,
        requesting_org_id: str,
        full_legal_name: str,
        date_of_birth: date,
        place_of_birth: str,
        nationality_at_birth: str,
        current_address: str,
        contact_email: str,
        contact_phone: str,
        current_nationality: str,
    ) -> Tuple[IdentityRecord, bool]:
        """
        Create a new Digital Identity.
        
        Args:
            requesting_org_id: ID of the organisation making the request
            full_legal_name: Individual's full legal name
            date_of_birth: Date of birth
            place_of_birth: Place of birth
            nationality_at_birth: Nationality at birth (ISO 3166-1 alpha-3)
            current_address: Current residential address
            contact_email: Contact email address
            contact_phone: Contact phone number
            current_nationality: Current nationality (ISO 3166-1 alpha-3)
            
        Returns:
            Tuple of (IdentityRecord, was_created) where was_created is False
            if an existing matching identity was returned (idempotent).
            
        Raises:
            AuthorisationDeniedError: If not Central Authority
        """
        self._verify_central_authority(requesting_org_id)
        
        immutable = ImmutableAttributes(
            full_legal_name=full_legal_name,
            date_of_birth=date_of_birth,
            place_of_birth=place_of_birth,
            nationality_at_birth=nationality_at_birth,
        )
        
        modifiable = ModifiableAttributes(
            current_address=current_address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            current_nationality=current_nationality,
        )
        
        return self._vault.store_identity(
            immutable_attrs=immutable,
            modifiable_attrs=modifiable,
            creating_authority=requesting_org_id,
        )
    
    def update_attribute(
        self,
        requesting_org_id: str,
        identity_ref: str,
        attribute_name: str,
        new_value: str,
    ) -> Tuple[str, str, bool]:
        """
        Update a modifiable attribute on an identity.
        
        Args:
            requesting_org_id: ID of the organisation making the request
            identity_ref: The identity to update
            attribute_name: Name of the attribute to modify
            new_value: The new value to set
            
        Returns:
            Tuple of (previous_value, new_value, was_changed)
            
        Raises:
            AuthorisationDeniedError: If not Central Authority
            IdentityNotFoundError: If identity doesn't exist
            ImmutableAttributeViolation: If attribute is immutable
            RevokedIdentityError: If identity is revoked
        """
        self._verify_central_authority(requesting_org_id)
        
        return self._attribute_keeper.update_attribute(
            identity_ref=identity_ref,
            attribute_name=attribute_name,
            new_value=new_value,
            authorising_entity=requesting_org_id,
        )
    
    def change_status(
        self,
        requesting_org_id: str,
        identity_ref: str,
        new_status: IdentityStatus,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """
        Change the status of a Digital Identity.
        
        Args:
            requesting_org_id: ID of the organisation making the request
            identity_ref: The identity to modify
            new_status: The target status
            reason: Optional reason for the change
            
        Returns:
            Tuple of (previous_status, new_status, was_changed)
            
        Raises:
            AuthorisationDeniedError: If not Central Authority
            IdentityNotFoundError: If identity doesn't exist
            RevokedIdentityError: If identity is already revoked
            InvalidStatusTransitionError: If transition is not valid
        """
        self._verify_central_authority(requesting_org_id)
        
        return self._status_sentinel.transition_status(
            identity_ref=identity_ref,
            target_status=new_status,
            authorising_entity=requesting_org_id,
            reason=reason,
        )
    
    def suspend_identity(
        self,
        requesting_org_id: str,
        identity_ref: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to suspend an identity."""
        return self.change_status(
            requesting_org_id,
            identity_ref,
            IdentityStatus.SUSPENDED,
            reason,
        )
    
    def reactivate_identity(
        self,
        requesting_org_id: str,
        identity_ref: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to reactivate a suspended identity."""
        return self.change_status(
            requesting_org_id,
            identity_ref,
            IdentityStatus.ACTIVE,
            reason,
        )
    
    def revoke_identity(
        self,
        requesting_org_id: str,
        identity_ref: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to permanently revoke an identity."""
        return self.change_status(
            requesting_org_id,
            identity_ref,
            IdentityStatus.REVOKED,
            reason,
        )
    
    def add_restriction(
        self,
        requesting_org_id: str,
        identity_ref: str,
        restriction_type: str,
        effective_date: date,
        expiry_date: Optional[date] = None,
        description: Optional[str] = None,
    ) -> TemporaryRestriction:
        """
        Add a temporary restriction to an identity.
        
        Args:
            requesting_org_id: ID of the organisation making the request
            identity_ref: The identity to modify
            restriction_type: Type identifier for the restriction
            effective_date: When the restriction takes effect
            expiry_date: Optional expiry date
            description: Optional description
            
        Returns:
            The created TemporaryRestriction
            
        Raises:
            AuthorisationDeniedError: If not Central Authority
            IdentityNotFoundError: If identity doesn't exist
        """
        self._verify_central_authority(requesting_org_id)
        
        restriction = TemporaryRestriction(
            restriction_type=restriction_type,
            effective_date=effective_date,
            expiry_date=expiry_date,
            description=description,
        )
        
        self._vault.add_temporary_restriction(identity_ref, restriction)
        return restriction
    
    def remove_restriction(
        self,
        requesting_org_id: str,
        identity_ref: str,
        restriction_type: str,
    ) -> bool:
        """
        Remove a temporary restriction from an identity.
        
        Returns True if a restriction was removed, False if none found.
        """
        self._verify_central_authority(requesting_org_id)
        return self._vault.remove_temporary_restriction(identity_ref, restriction_type)
    
    def get_identity(self, identity_ref: str) -> IdentityRecord:
        """
        Retrieve an identity record.
        
        Note: This is a direct retrieval without access control.
        For controlled access, use the verification services.
        """
        return self._vault.retrieve_identity(identity_ref)
    
    def identity_exists(self, identity_ref: str) -> bool:
        """Check if an identity exists."""
        return self._vault.identity_exists(identity_ref)
    
    def register_organisation(
        self,
        requesting_org_id: str,
        org_name: str,
        org_type: OrganisationType,
        access_tier: Optional[AccessTier] = None,
        contact_email: Optional[str] = None,
    ):
        """
        Register a new consuming organisation.
        
        Only the Central Authority can register organisations.
        """
        self._verify_central_authority(requesting_org_id)
        
        return self._registry.register_organisation(
            org_name=org_name,
            org_type=org_type,
            access_tier=access_tier,
            contact_email=contact_email,
        )
    
    def deactivate_organisation(
        self,
        requesting_org_id: str,
        target_org_id: str,
    ) -> bool:
        """
        Deactivate a consuming organisation.
        
        Only the Central Authority can deactivate organisations.
        """
        self._verify_central_authority(requesting_org_id)
        return self._registry.deactivate_organisation(target_org_id)
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get overview statistics of the system.
        
        Returns counts of identities by status and organisations by tier.
        """
        all_refs = self._vault.get_all_identity_refs()
        
        status_counts = {
            "ACTIVE": 0,
            "SUSPENDED": 0,
            "REVOKED": 0,
        }
        
        for ref in all_refs:
            record = self._vault.retrieve_identity(ref)
            status_counts[record.current_status.value] += 1
        
        org_counts = {
            "BASIC": 0,
            "STANDARD": 0,
            "ENHANCED": 0,
        }
        
        for org in self._registry.get_all_organisations():
            org_counts[org.access_tier.value] += 1
        
        return {
            "total_identities": len(all_refs),
            "identities_by_status": status_counts,
            "total_organisations": self._registry.count_organisations(),
            "organisations_by_tier": org_counts,
        }
