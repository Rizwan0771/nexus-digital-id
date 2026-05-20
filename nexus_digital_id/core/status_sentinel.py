"""
Nexus Digital ID - Status Sentinel

Manages the lifecycle status of Digital Identities with strict
transition rules and comprehensive audit trail maintenance.

Status Lifecycle:
    ACTIVE <-> SUSPENDED (bidirectional)
    ACTIVE -> REVOKED (terminal)
    SUSPENDED -> REVOKED (terminal)
    REVOKED -> (no transitions permitted)
"""

from datetime import datetime
from typing import Optional, Tuple

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityRecord,
    IdentityStatus,
    StatusHistoryEntry,
)
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    RevokedIdentityError,
    InvalidStatusTransitionError,
)


class StatusSentinel:
    """
    Guardian of Digital Identity status transitions.
    
    Enforces valid state transitions and maintains complete
    history of all status changes for audit purposes.
    
    Valid Transitions:
    - ACTIVE -> SUSPENDED: Temporary deactivation
    - SUSPENDED -> ACTIVE: Reactivation
    - ACTIVE -> REVOKED: Permanent termination
    - SUSPENDED -> REVOKED: Permanent termination
    
    Invalid Transitions:
    - REVOKED -> Any: Terminal state, no changes allowed
    - Same -> Same: No-op, but rejected to ensure intentional changes
    """
    
    # Define valid transitions as (from_status, to_status) pairs
    _PERMITTED_TRANSITIONS = frozenset([
        (IdentityStatus.ACTIVE, IdentityStatus.SUSPENDED),
        (IdentityStatus.SUSPENDED, IdentityStatus.ACTIVE),
        (IdentityStatus.ACTIVE, IdentityStatus.REVOKED),
        (IdentityStatus.SUSPENDED, IdentityStatus.REVOKED),
    ])
    
    def __init__(self, identity_vault: DigitalIdentityVault):
        """
        Initialise the Status Sentinel.
        
        Args:
            identity_vault: The vault containing identity records to manage
        """
        self._vault = identity_vault
    
    def transition_status(
        self,
        identity_ref: str,
        target_status: IdentityStatus,
        authorising_entity: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """
        Attempt to transition an identity to a new status.
        
        Args:
            identity_ref: The identity to modify
            target_status: The desired new status
            authorising_entity: Who is authorising this change
            reason: Optional explanation for the transition
            
        Returns:
            Tuple of (previous_status, new_status, was_changed) where
            was_changed indicates if a transition actually occurred.
            
        Raises:
            IdentityNotFoundError: If identity doesn't exist
            RevokedIdentityError: If identity is already revoked
            InvalidStatusTransitionError: If transition is not permitted
        """
        record = self._vault.retrieve_identity(identity_ref)
        current_status = record.current_status
        
        # Check for revoked identity (terminal state)
        if current_status == IdentityStatus.REVOKED:
            raise RevokedIdentityError(identity_ref, "status_change")
        
        # Check for same-status transition (no-op but rejected)
        if current_status == target_status:
            raise InvalidStatusTransitionError(
                current_status.value,
                target_status.value,
                identity_ref
            )
        
        # Validate transition is permitted
        transition = (current_status, target_status)
        if transition not in self._PERMITTED_TRANSITIONS:
            raise InvalidStatusTransitionError(
                current_status.value,
                target_status.value,
                identity_ref
            )
        
        # Execute the transition
        transition_time = datetime.utcnow()
        
        history_entry = StatusHistoryEntry(
            previous_status=current_status,
            new_status=target_status,
            transition_timestamp=transition_time,
            authorising_entity=authorising_entity,
            reason=reason,
        )
        
        record.current_status = target_status
        record.status_history.append(history_entry)
        
        return current_status, target_status, True
    
    def get_current_status(self, identity_ref: str) -> IdentityStatus:
        """
        Retrieve the current status of an identity.
        
        Args:
            identity_ref: The identity to check
            
        Returns:
            The current IdentityStatus
            
        Raises:
            IdentityNotFoundError: If identity doesn't exist
        """
        record = self._vault.retrieve_identity(identity_ref)
        return record.current_status
    
    def is_active(self, identity_ref: str) -> bool:
        """Check if an identity is currently active."""
        return self.get_current_status(identity_ref) == IdentityStatus.ACTIVE
    
    def is_suspended(self, identity_ref: str) -> bool:
        """Check if an identity is currently suspended."""
        return self.get_current_status(identity_ref) == IdentityStatus.SUSPENDED
    
    def is_revoked(self, identity_ref: str) -> bool:
        """Check if an identity has been permanently revoked."""
        return self.get_current_status(identity_ref) == IdentityStatus.REVOKED
    
    def can_transition_to(self, identity_ref: str, target_status: IdentityStatus) -> bool:
        """
        Check if a transition to the target status would be valid.
        
        Does not modify any state, just validates the transition.
        """
        try:
            record = self._vault.retrieve_identity(identity_ref)
        except IdentityNotFoundError:
            return False
        
        current_status = record.current_status
        
        if current_status == IdentityStatus.REVOKED:
            return False
        
        if current_status == target_status:
            return False
        
        return (current_status, target_status) in self._PERMITTED_TRANSITIONS
    
    def get_status_history(self, identity_ref: str) -> list:
        """
        Retrieve the complete status history for an identity.
        
        Returns list of StatusHistoryEntry objects in chronological order.
        """
        record = self._vault.retrieve_identity(identity_ref)
        return record.status_history.copy()
    
    def suspend_identity(
        self,
        identity_ref: str,
        authorising_entity: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to suspend an active identity."""
        return self.transition_status(
            identity_ref,
            IdentityStatus.SUSPENDED,
            authorising_entity,
            reason,
        )
    
    def reactivate_identity(
        self,
        identity_ref: str,
        authorising_entity: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to reactivate a suspended identity."""
        return self.transition_status(
            identity_ref,
            IdentityStatus.ACTIVE,
            authorising_entity,
            reason,
        )
    
    def revoke_identity(
        self,
        identity_ref: str,
        authorising_entity: str,
        reason: Optional[str] = None,
    ) -> Tuple[IdentityStatus, IdentityStatus, bool]:
        """Convenience method to permanently revoke an identity."""
        return self.transition_status(
            identity_ref,
            IdentityStatus.REVOKED,
            authorising_entity,
            reason,
        )
