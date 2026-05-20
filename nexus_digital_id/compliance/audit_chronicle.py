"""
Nexus Digital ID - Audit Chronicle

Comprehensive audit logging system that records all significant
system actions for compliance and forensic purposes.

All entries are stored in append-only fashion with unique identifiers
and ISO 8601 timestamps.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class AuditEventType(Enum):
    """Classification of auditable events in the system."""
    IDENTITY_CREATED = "IDENTITY_CREATED"
    IDENTITY_ATTRIBUTE_UPDATED = "IDENTITY_ATTRIBUTE_UPDATED"
    IDENTITY_STATUS_CHANGED = "IDENTITY_STATUS_CHANGED"
    RESTRICTION_ADDED = "RESTRICTION_ADDED"
    RESTRICTION_REMOVED = "RESTRICTION_REMOVED"
    VERIFICATION_PERFORMED = "VERIFICATION_PERFORMED"
    ORGANISATION_REGISTERED = "ORGANISATION_REGISTERED"
    ORGANISATION_DEACTIVATED = "ORGANISATION_DEACTIVATED"
    AUTHORISATION_DENIED = "AUTHORISATION_DENIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    BUSINESS_RULE_VIOLATED = "BUSINESS_RULE_VIOLATED"


@dataclass
class AuditEntry:
    """
    A single audit log entry.
    
    Contains all information needed to reconstruct what action
    occurred, when, and by whom.
    """
    entry_id: str
    event_type: AuditEventType
    timestamp: datetime
    actor_id: str
    identity_ref: Optional[str]
    details: Dict[str, Any]
    outcome: str  # "SUCCESS" or "FAILURE"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialisation."""
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "identity_ref": self.identity_ref,
            "details": self.details,
            "outcome": self.outcome,
        }
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"[{self.timestamp.isoformat()}] {self.event_type.value} "
            f"by {self.actor_id} - {self.outcome}"
        )


class AuditChronicle:
    """
    Append-only audit log for the Digital ID system.
    
    Records all significant actions with full context for
    compliance, debugging, and forensic analysis.
    
    Features:
    - Unique entry IDs for each log entry
    - ISO 8601 timestamps in UTC
    - Append-only storage (entries cannot be modified or deleted)
    - Filtering by identity, actor, event type, and time range
    """
    
    def __init__(self):
        """Initialise empty audit chronicle."""
        self._entries: List[AuditEntry] = []
        self._entry_index: Dict[str, int] = {}  # entry_id -> index
        self._identity_index: Dict[str, List[str]] = {}  # identity_ref -> [entry_ids]
    
    def _generate_entry_id(self) -> str:
        """Generate a unique entry identifier."""
        return f"AUD-{uuid.uuid4().hex[:12].upper()}"
    
    def record(
        self,
        event_type: AuditEventType,
        actor_id: str,
        identity_ref: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        outcome: str = "SUCCESS",
    ) -> AuditEntry:
        """
        Record a new audit entry.
        
        Args:
            event_type: Classification of the event
            actor_id: ID of the entity performing the action
            identity_ref: Related Digital ID (if applicable)
            details: Additional context about the event
            outcome: "SUCCESS" or "FAILURE"
            
        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            entry_id=self._generate_entry_id(),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            actor_id=actor_id,
            identity_ref=identity_ref,
            details=details or {},
            outcome=outcome,
        )
        
        # Append to main list
        index = len(self._entries)
        self._entries.append(entry)
        
        # Update indices
        self._entry_index[entry.entry_id] = index
        
        if identity_ref:
            if identity_ref not in self._identity_index:
                self._identity_index[identity_ref] = []
            self._identity_index[identity_ref].append(entry.entry_id)
        
        return entry
    
    def record_identity_creation(
        self,
        actor_id: str,
        identity_ref: str,
        was_new: bool,
    ) -> AuditEntry:
        """Record an identity creation event."""
        return self.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details={
                "was_new_creation": was_new,
                "action": "create_identity",
            },
        )
    
    def record_attribute_update(
        self,
        actor_id: str,
        identity_ref: str,
        attribute_name: str,
        previous_value: str,
        new_value: str,
        was_changed: bool,
    ) -> AuditEntry:
        """Record an attribute update event."""
        return self.record(
            event_type=AuditEventType.IDENTITY_ATTRIBUTE_UPDATED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details={
                "attribute_name": attribute_name,
                "previous_value": previous_value,
                "new_value": new_value,
                "was_changed": was_changed,
                "action": "update_attribute",
            },
        )
    
    def record_status_change(
        self,
        actor_id: str,
        identity_ref: str,
        previous_status: str,
        new_status: str,
        reason: Optional[str] = None,
    ) -> AuditEntry:
        """Record a status change event."""
        return self.record(
            event_type=AuditEventType.IDENTITY_STATUS_CHANGED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details={
                "previous_status": previous_status,
                "new_status": new_status,
                "reason": reason,
                "action": "change_status",
            },
        )
    
    def record_verification(
        self,
        actor_id: str,
        identity_ref: str,
        verification_type: str,
        result: str,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record a verification request event."""
        details = {
            "verification_type": verification_type,
            "result": result,
            "action": "verify_identity",
        }
        if additional_details:
            details.update(additional_details)
        
        return self.record(
            event_type=AuditEventType.VERIFICATION_PERFORMED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details=details,
        )
    
    def record_authorisation_denied(
        self,
        actor_id: str,
        attempted_operation: str,
        reason: str,
        identity_ref: Optional[str] = None,
    ) -> AuditEntry:
        """Record an authorisation denial event."""
        return self.record(
            event_type=AuditEventType.AUTHORISATION_DENIED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details={
                "attempted_operation": attempted_operation,
                "denial_reason": reason,
            },
            outcome="FAILURE",
        )
    
    def record_validation_failure(
        self,
        actor_id: str,
        request_type: str,
        failures: List[str],
        identity_ref: Optional[str] = None,
    ) -> AuditEntry:
        """Record a validation failure event."""
        return self.record(
            event_type=AuditEventType.VALIDATION_FAILED,
            actor_id=actor_id,
            identity_ref=identity_ref,
            details={
                "request_type": request_type,
                "validation_failures": failures,
            },
            outcome="FAILURE",
        )
    
    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve a specific audit entry by ID."""
        index = self._entry_index.get(entry_id)
        if index is not None:
            return self._entries[index]
        return None
    
    def get_entries_for_identity(self, identity_ref: str) -> List[AuditEntry]:
        """Retrieve all audit entries for a specific identity."""
        entry_ids = self._identity_index.get(identity_ref, [])
        return [self._entries[self._entry_index[eid]] for eid in entry_ids]
    
    def get_entries_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[AuditEntry]:
        """Retrieve all entries within a time range."""
        return [
            entry for entry in self._entries
            if start_time <= entry.timestamp <= end_time
        ]
    
    def get_entries_by_event_type(
        self,
        event_type: AuditEventType,
    ) -> List[AuditEntry]:
        """Retrieve all entries of a specific event type."""
        return [
            entry for entry in self._entries
            if entry.event_type == event_type
        ]
    
    def get_entries_by_actor(self, actor_id: str) -> List[AuditEntry]:
        """Retrieve all entries for a specific actor."""
        return [
            entry for entry in self._entries
            if entry.actor_id == actor_id
        ]
    
    def get_all_entries(self) -> List[AuditEntry]:
        """Retrieve all audit entries in chronological order."""
        return self._entries.copy()
    
    def count_entries(self) -> int:
        """Return total number of audit entries."""
        return len(self._entries)
    
    def get_recent_entries(self, count: int = 10) -> List[AuditEntry]:
        """Retrieve the most recent entries."""
        return self._entries[-count:] if self._entries else []
