"""
Nexus Digital ID - Attribute Keeper

Manages the modification of Digital Identity attributes with strict
enforcement of immutability rules and comprehensive change tracking.

Attribute Categories:
- Immutable: Cannot be changed after creation (DOB, place of birth, etc.)
- Modifiable: Can be updated by Central Authority (address, contact info)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityRecord,
    IdentityStatus,
)
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    ImmutableAttributeViolation,
    RevokedIdentityError,
)


@dataclass
class AttributeChangeRecord:
    """
    Record of an attribute modification for audit purposes.
    
    Captures the complete context of each attribute change including
    previous and new values, timing, and authorising entity.
    """
    identity_ref: str
    attribute_name: str
    previous_value: str
    new_value: str
    change_timestamp: datetime
    authorising_entity: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialisation."""
        return {
            "identity_ref": self.identity_ref,
            "attribute_name": self.attribute_name,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "change_timestamp": self.change_timestamp.isoformat(),
            "authorising_entity": self.authorising_entity,
        }


class AttributeKeeper:
    """
    Guardian of Digital Identity attribute modifications.
    
    Enforces immutability rules and tracks all changes to modifiable
    attributes for audit and compliance purposes.
    
    Immutable Attributes (cannot be changed):
    - full_legal_name
    - date_of_birth
    - place_of_birth
    - nationality_at_birth
    - identity_ref
    - creation_timestamp
    
    Modifiable Attributes (Central Authority only):
    - current_address
    - contact_email
    - contact_phone
    - current_nationality
    """
    
    # Define attribute categories
    IMMUTABLE_ATTRIBUTES = frozenset([
        "full_legal_name",
        "date_of_birth",
        "place_of_birth",
        "nationality_at_birth",
        "identity_ref",
        "creation_timestamp",
    ])
    
    MODIFIABLE_ATTRIBUTES = frozenset([
        "current_address",
        "contact_email",
        "contact_phone",
        "current_nationality",
    ])
    
    def __init__(self, identity_vault: DigitalIdentityVault):
        """
        Initialise the Attribute Keeper.
        
        Args:
            identity_vault: The vault containing identity records to manage
        """
        self._vault = identity_vault
        self._change_history: List[AttributeChangeRecord] = []
    
    def update_attribute(
        self,
        identity_ref: str,
        attribute_name: str,
        new_value: str,
        authorising_entity: str,
    ) -> Tuple[str, str, bool]:
        """
        Update a modifiable attribute on an identity.
        
        Args:
            identity_ref: The identity to modify
            attribute_name: Name of the attribute to update
            new_value: The new value to set
            authorising_entity: Who is authorising this change
            
        Returns:
            Tuple of (previous_value, new_value, was_changed) where
            was_changed is False if the value was already set to new_value.
            
        Raises:
            IdentityNotFoundError: If identity doesn't exist
            ImmutableAttributeViolation: If attempting to modify immutable field
            RevokedIdentityError: If identity has been revoked
        """
        # Retrieve and validate identity exists
        record = self._vault.retrieve_identity(identity_ref)
        
        # Check if identity is revoked
        if record.current_status == IdentityStatus.REVOKED:
            raise RevokedIdentityError(identity_ref, "attribute_update")
        
        # Check if attribute is immutable
        if attribute_name in self.IMMUTABLE_ATTRIBUTES:
            raise ImmutableAttributeViolation(attribute_name)
        
        # Check if attribute is valid modifiable attribute
        if attribute_name not in self.MODIFIABLE_ATTRIBUTES:
            raise ImmutableAttributeViolation(attribute_name)
        
        # Perform the update via vault
        old_value, new_value, was_changed = self._vault.update_modifiable_attribute(
            identity_ref,
            attribute_name,
            new_value,
        )
        
        # Record the change if it actually occurred
        if was_changed:
            change_record = AttributeChangeRecord(
                identity_ref=identity_ref,
                attribute_name=attribute_name,
                previous_value=old_value,
                new_value=new_value,
                change_timestamp=datetime.utcnow(),
                authorising_entity=authorising_entity,
            )
            self._change_history.append(change_record)
        
        return old_value, new_value, was_changed
    
    def get_attribute_value(
        self,
        identity_ref: str,
        attribute_name: str,
    ) -> Any:
        """
        Retrieve the current value of an attribute.
        
        Args:
            identity_ref: The identity to query
            attribute_name: Name of the attribute to retrieve
            
        Returns:
            The current value of the attribute
            
        Raises:
            IdentityNotFoundError: If identity doesn't exist
            ValueError: If attribute name is not recognised
        """
        record = self._vault.retrieve_identity(identity_ref)
        
        # Check immutable attributes
        if attribute_name in self.IMMUTABLE_ATTRIBUTES:
            if attribute_name == "identity_ref":
                return record.identity_ref
            elif attribute_name == "creation_timestamp":
                return record.creation_timestamp
            else:
                return getattr(record.immutable_attrs, attribute_name)
        
        # Check modifiable attributes
        if attribute_name in self.MODIFIABLE_ATTRIBUTES:
            return getattr(record.modifiable_attrs, attribute_name)
        
        raise ValueError(f"Unknown attribute: {attribute_name}")
    
    def get_all_attributes(
        self,
        identity_ref: str,
        include_immutable: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve all attributes for an identity.
        
        Args:
            identity_ref: The identity to query
            include_immutable: Whether to include immutable attributes
            
        Returns:
            Dictionary of attribute names to values
        """
        record = self._vault.retrieve_identity(identity_ref)
        
        result = {}
        
        if include_immutable:
            result["identity_ref"] = record.identity_ref
            result["creation_timestamp"] = record.creation_timestamp.isoformat()
            result["full_legal_name"] = record.immutable_attrs.full_legal_name
            result["date_of_birth"] = record.immutable_attrs.date_of_birth.isoformat()
            result["place_of_birth"] = record.immutable_attrs.place_of_birth
            result["nationality_at_birth"] = record.immutable_attrs.nationality_at_birth
        
        result["current_address"] = record.modifiable_attrs.current_address
        result["contact_email"] = record.modifiable_attrs.contact_email
        result["contact_phone"] = record.modifiable_attrs.contact_phone
        result["current_nationality"] = record.modifiable_attrs.current_nationality
        
        return result
    
    def is_attribute_immutable(self, attribute_name: str) -> bool:
        """Check if an attribute is immutable."""
        return attribute_name in self.IMMUTABLE_ATTRIBUTES
    
    def is_attribute_modifiable(self, attribute_name: str) -> bool:
        """Check if an attribute can be modified."""
        return attribute_name in self.MODIFIABLE_ATTRIBUTES
    
    def get_change_history(
        self,
        identity_ref: Optional[str] = None,
    ) -> List[AttributeChangeRecord]:
        """
        Retrieve attribute change history.
        
        Args:
            identity_ref: If provided, filter to changes for this identity only
            
        Returns:
            List of AttributeChangeRecord objects in chronological order
        """
        if identity_ref:
            return [
                record for record in self._change_history
                if record.identity_ref == identity_ref
            ]
        return self._change_history.copy()
    
    def get_change_history_for_attribute(
        self,
        identity_ref: str,
        attribute_name: str,
    ) -> List[AttributeChangeRecord]:
        """
        Retrieve change history for a specific attribute on an identity.
        
        Returns list of changes in chronological order.
        """
        return [
            record for record in self._change_history
            if record.identity_ref == identity_ref
            and record.attribute_name == attribute_name
        ]
    
    def clear_change_history(self) -> None:
        """Clear the change history. Use with caution."""
        self._change_history.clear()
