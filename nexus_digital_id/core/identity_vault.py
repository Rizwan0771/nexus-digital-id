"""
Nexus Digital ID - Identity Vault

The central repository for Digital Identity records. Implements the core
data model with immutable and modifiable attributes, status tracking,
and comprehensive history management.

Design Principles:
- Immutability for core identity attributes
- Full audit trail of all modifications
- Thread-safe operations (single-threaded console app)
- Deterministic behaviour for repeated operations
"""

import uuid
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    DuplicateIdentityError,
    ImmutableAttributeViolation,
)


class IdentityStatus(Enum):
    """
    Possible states for a Digital Identity.
    
    State Transitions:
    - ACTIVE -> SUSPENDED (reversible)
    - SUSPENDED -> ACTIVE (reversible)
    - ACTIVE -> REVOKED (terminal)
    - SUSPENDED -> REVOKED (terminal)
    - REVOKED -> (no transitions allowed)
    """
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class ImmutableAttributes:
    """
    Identity attributes that cannot be changed after creation.
    
    These represent fundamental identity characteristics that
    remain constant throughout an individual's lifetime.
    """
    full_legal_name: str
    date_of_birth: date
    place_of_birth: str
    nationality_at_birth: str  # ISO 3166-1 alpha-3 code
    
    def compute_fingerprint(self) -> str:
        """
        Generate a unique fingerprint for duplicate detection.
        
        Uses SHA-256 hash of normalised attribute values to enable
        idempotent creation operations.
        """
        normalised = (
            f"{self.full_legal_name.lower().strip()}|"
            f"{self.date_of_birth.isoformat()}|"
            f"{self.place_of_birth.lower().strip()}|"
            f"{self.nationality_at_birth.upper()}"
        )
        return hashlib.sha256(normalised.encode()).hexdigest()[:16]


@dataclass
class ModifiableAttributes:
    """
    Identity attributes that can be updated by the Central Authority.
    
    These represent changeable life circumstances that may need
    periodic updates to maintain accuracy.
    """
    current_address: str
    contact_email: str
    contact_phone: str
    current_nationality: str  # ISO 3166-1 alpha-3 code
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialisation."""
        return {
            "current_address": self.current_address,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "current_nationality": self.current_nationality,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ModifiableAttributes":
        """Create instance from dictionary."""
        return cls(
            current_address=data["current_address"],
            contact_email=data["contact_email"],
            contact_phone=data["contact_phone"],
            current_nationality=data["current_nationality"],
        )


@dataclass
class StatusHistoryEntry:
    """
    Record of a status transition for audit purposes.
    
    Captures the complete context of each status change including
    who authorised it and when it occurred.
    """
    previous_status: Optional[IdentityStatus]
    new_status: IdentityStatus
    transition_timestamp: datetime
    authorising_entity: str
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialisation."""
        return {
            "previous_status": self.previous_status.value if self.previous_status else None,
            "new_status": self.new_status.value,
            "transition_timestamp": self.transition_timestamp.isoformat(),
            "authorising_entity": self.authorising_entity,
            "reason": self.reason,
        }


@dataclass
class TemporaryRestriction:
    """
    A time-bound restriction applied to a Digital Identity.
    
    Used for conditions like driving restrictions, travel limitations,
    or other temporary constraints that affect verification outcomes.
    """
    restriction_type: str
    effective_date: date
    expiry_date: Optional[date] = None
    description: Optional[str] = None
    
    def is_active(self, check_date: Optional[date] = None) -> bool:
        """Determine if restriction is currently in effect."""
        check = check_date or date.today()
        if check < self.effective_date:
            return False
        if self.expiry_date and check > self.expiry_date:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialisation."""
        return {
            "restriction_type": self.restriction_type,
            "effective_date": self.effective_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "description": self.description,
        }


@dataclass
class IdentityRecord:
    """
    Complete Digital Identity record.
    
    Combines immutable core attributes with modifiable details,
    status information, and full history tracking.
    """
    identity_ref: str  # Unique identifier (DID-xxxxxxxx format)
    creation_timestamp: datetime
    immutable_attrs: ImmutableAttributes
    modifiable_attrs: ModifiableAttributes
    current_status: IdentityStatus
    status_history: List[StatusHistoryEntry] = field(default_factory=list)
    temporary_restrictions: List[TemporaryRestriction] = field(default_factory=list)
    attribute_fingerprint: str = ""
    
    def __post_init__(self):
        """Compute fingerprint if not provided."""
        if not self.attribute_fingerprint:
            self.attribute_fingerprint = self.immutable_attrs.compute_fingerprint()
    
    def has_active_restrictions(self, check_date: Optional[date] = None) -> bool:
        """Check if any temporary restrictions are currently active."""
        return any(r.is_active(check_date) for r in self.temporary_restrictions)
    
    def get_active_restrictions(self, check_date: Optional[date] = None) -> List[TemporaryRestriction]:
        """Retrieve all currently active restrictions."""
        return [r for r in self.temporary_restrictions if r.is_active(check_date)]
    
    def was_suspended_during_period(self, start_date: date, end_date: date) -> tuple[bool, List[Dict]]:
        """
        Check if identity was suspended at any point during a period.
        
        Returns:
            Tuple of (was_suspended, list of suspension periods overlapping the range)
        """
        suspension_periods = []
        
        for i, entry in enumerate(self.status_history):
            if entry.new_status == IdentityStatus.SUSPENDED:
                suspension_start = entry.transition_timestamp.date()
                
                # Find when suspension ended (if it did)
                suspension_end = None
                for later_entry in self.status_history[i+1:]:
                    if later_entry.new_status in (IdentityStatus.ACTIVE, IdentityStatus.REVOKED):
                        suspension_end = later_entry.transition_timestamp.date()
                        break
                
                # Check for overlap with requested period
                if suspension_end is None:
                    suspension_end = date.today()
                
                # Periods overlap if: start1 <= end2 AND start2 <= end1
                if suspension_start <= end_date and start_date <= suspension_end:
                    overlap_start = max(suspension_start, start_date)
                    overlap_end = min(suspension_end, end_date)
                    suspension_periods.append({
                        "suspension_start": overlap_start.isoformat(),
                        "suspension_end": overlap_end.isoformat(),
                    })
        
        return len(suspension_periods) > 0, suspension_periods
    
    def to_dict(self, include_history: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for serialisation.
        
        Args:
            include_history: Whether to include full status history
        """
        result = {
            "identity_ref": self.identity_ref,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "current_status": self.current_status.value,
            "immutable_attributes": {
                "full_legal_name": self.immutable_attrs.full_legal_name,
                "date_of_birth": self.immutable_attrs.date_of_birth.isoformat(),
                "place_of_birth": self.immutable_attrs.place_of_birth,
                "nationality_at_birth": self.immutable_attrs.nationality_at_birth,
            },
            "modifiable_attributes": self.modifiable_attrs.to_dict(),
            "has_active_restrictions": self.has_active_restrictions(),
        }
        
        if include_history:
            result["status_history"] = [e.to_dict() for e in self.status_history]
            result["temporary_restrictions"] = [r.to_dict() for r in self.temporary_restrictions]
        
        return result


class DigitalIdentityVault:
    """
    Central storage and management facility for Digital Identity records.
    
    Provides CRUD operations with built-in duplicate detection,
    fingerprint-based idempotency, and comprehensive error handling.
    
    Thread Safety: This implementation is designed for single-threaded
    console application use. For concurrent access, external locking
    would be required.
    """
    
    # Class-level constants for ID generation
    _ID_PREFIX = "DID"
    _IMMUTABLE_FIELDS = frozenset([
        "full_legal_name",
        "date_of_birth", 
        "place_of_birth",
        "nationality_at_birth",
        "identity_ref",
        "creation_timestamp",
    ])
    _MODIFIABLE_FIELDS = frozenset([
        "current_address",
        "contact_email",
        "contact_phone",
        "current_nationality",
    ])
    
    def __init__(self):
        """Initialise empty vault."""
        self._records: Dict[str, IdentityRecord] = {}
        self._fingerprint_index: Dict[str, str] = {}  # fingerprint -> identity_ref
    
    def _generate_identity_ref(self) -> str:
        """Generate a unique identity reference in DID-xxxxxxxx format."""
        unique_part = uuid.uuid4().hex[:8]
        return f"{self._ID_PREFIX}-{unique_part}"
    
    def store_identity(
        self,
        immutable_attrs: ImmutableAttributes,
        modifiable_attrs: ModifiableAttributes,
        creating_authority: str,
    ) -> tuple[IdentityRecord, bool]:
        """
        Store a new Digital Identity in the vault.
        
        Implements idempotent creation - if an identity with matching
        immutable attributes already exists, returns the existing record.
        
        Args:
            immutable_attrs: Core identity attributes (cannot be changed)
            modifiable_attrs: Updateable contact/address information
            creating_authority: Identifier of the authority creating this ID
            
        Returns:
            Tuple of (IdentityRecord, was_created) where was_created is False
            if an existing matching record was returned.
            
        Raises:
            DuplicateIdentityError: If duplicate detection fails unexpectedly
        """
        fingerprint = immutable_attrs.compute_fingerprint()
        
        # Check for existing identity with same fingerprint (idempotent creation)
        if fingerprint in self._fingerprint_index:
            existing_ref = self._fingerprint_index[fingerprint]
            return self._records[existing_ref], False
        
        # Create new identity
        identity_ref = self._generate_identity_ref()
        creation_time = datetime.utcnow()
        
        initial_status_entry = StatusHistoryEntry(
            previous_status=None,
            new_status=IdentityStatus.ACTIVE,
            transition_timestamp=creation_time,
            authorising_entity=creating_authority,
            reason="Initial creation",
        )
        
        record = IdentityRecord(
            identity_ref=identity_ref,
            creation_timestamp=creation_time,
            immutable_attrs=immutable_attrs,
            modifiable_attrs=modifiable_attrs,
            current_status=IdentityStatus.ACTIVE,
            status_history=[initial_status_entry],
            attribute_fingerprint=fingerprint,
        )
        
        self._records[identity_ref] = record
        self._fingerprint_index[fingerprint] = identity_ref
        
        return record, True
    
    def retrieve_identity(self, identity_ref: str) -> IdentityRecord:
        """
        Retrieve a Digital Identity by its reference.
        
        Args:
            identity_ref: The unique identifier (DID-xxxxxxxx)
            
        Returns:
            The matching IdentityRecord
            
        Raises:
            IdentityNotFoundError: If no matching identity exists
        """
        if identity_ref not in self._records:
            raise IdentityNotFoundError(identity_ref)
        return self._records[identity_ref]
    
    def identity_exists(self, identity_ref: str) -> bool:
        """Check if an identity reference exists in the vault."""
        return identity_ref in self._records
    
    def update_modifiable_attribute(
        self,
        identity_ref: str,
        attribute_name: str,
        new_value: str,
    ) -> tuple[str, str, bool]:
        """
        Update a modifiable attribute on an existing identity.
        
        Args:
            identity_ref: The identity to update
            attribute_name: Name of the attribute to modify
            new_value: The new value to set
            
        Returns:
            Tuple of (old_value, new_value, was_changed) where was_changed
            is False if the new value matches the existing value.
            
        Raises:
            IdentityNotFoundError: If identity doesn't exist
            ImmutableAttributeViolation: If attempting to modify immutable field
        """
        if identity_ref not in self._records:
            raise IdentityNotFoundError(identity_ref)
        
        if attribute_name in self._IMMUTABLE_FIELDS:
            raise ImmutableAttributeViolation(attribute_name)
        
        if attribute_name not in self._MODIFIABLE_FIELDS:
            raise ImmutableAttributeViolation(attribute_name)
        
        record = self._records[identity_ref]
        old_value = getattr(record.modifiable_attrs, attribute_name)
        
        # Idempotent update - no change if values match
        if old_value == new_value:
            return old_value, new_value, False
        
        setattr(record.modifiable_attrs, attribute_name, new_value)
        return old_value, new_value, True
    
    def add_temporary_restriction(
        self,
        identity_ref: str,
        restriction: TemporaryRestriction,
    ) -> None:
        """Add a temporary restriction to an identity."""
        if identity_ref not in self._records:
            raise IdentityNotFoundError(identity_ref)
        
        self._records[identity_ref].temporary_restrictions.append(restriction)
    
    def remove_temporary_restriction(
        self,
        identity_ref: str,
        restriction_type: str,
    ) -> bool:
        """
        Remove a temporary restriction by type.
        
        Returns True if a restriction was removed, False if none found.
        """
        if identity_ref not in self._records:
            raise IdentityNotFoundError(identity_ref)
        
        record = self._records[identity_ref]
        original_count = len(record.temporary_restrictions)
        record.temporary_restrictions = [
            r for r in record.temporary_restrictions 
            if r.restriction_type != restriction_type
        ]
        return len(record.temporary_restrictions) < original_count
    
    def get_all_identity_refs(self) -> List[str]:
        """Return list of all identity references in the vault."""
        return list(self._records.keys())
    
    def count_identities(self) -> int:
        """Return total number of identities in the vault."""
        return len(self._records)
    
    def clear_vault(self) -> None:
        """Remove all identities from the vault. Use with caution."""
        self._records.clear()
        self._fingerprint_index.clear()
