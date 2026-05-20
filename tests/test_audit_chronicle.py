"""
Nexus Digital ID - Audit Chronicle Tests

Tests for the audit logging system.
"""

import pytest
from datetime import datetime, timedelta

from nexus_digital_id.compliance.audit_chronicle import (
    AuditChronicle,
    AuditEntry,
    AuditEventType,
)


class TestAuditRecording:
    """Tests for recording audit entries."""
    
    def test_record_creates_entry(self, audit_chronicle):
        """Should create an audit entry."""
        entry = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="TEST-ACTOR",
            identity_ref="DID-12345678",
            details={"test": "data"},
        )
        
        assert entry is not None
        assert entry.entry_id.startswith("AUD-")
        assert entry.event_type == AuditEventType.IDENTITY_CREATED
    
    def test_record_assigns_unique_ids(self, audit_chronicle):
        """Each entry should have a unique ID."""
        entry1 = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
        )
        entry2 = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
        )
        
        assert entry1.entry_id != entry2.entry_id
    
    def test_record_includes_timestamp(self, audit_chronicle):
        """Entries should have timestamps."""
        entry = audit_chronicle.record(
            event_type=AuditEventType.VERIFICATION_PERFORMED,
            actor_id="ACTOR",
        )
        
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)
    
    def test_record_identity_creation(self, audit_chronicle):
        """Should record identity creation events."""
        entry = audit_chronicle.record_identity_creation(
            actor_id="CENTRAL-001",
            identity_ref="DID-abcd1234",
            was_new=True,
        )
        
        assert entry.event_type == AuditEventType.IDENTITY_CREATED
        assert entry.details["was_new_creation"] is True
    
    def test_record_attribute_update(self, audit_chronicle):
        """Should record attribute update events."""
        entry = audit_chronicle.record_attribute_update(
            actor_id="CENTRAL-001",
            identity_ref="DID-abcd1234",
            attribute_name="current_address",
            previous_value="Old Address",
            new_value="New Address",
            was_changed=True,
        )
        
        assert entry.event_type == AuditEventType.IDENTITY_ATTRIBUTE_UPDATED
        assert entry.details["attribute_name"] == "current_address"
        assert entry.details["previous_value"] == "Old Address"
        assert entry.details["new_value"] == "New Address"
    
    def test_record_status_change(self, audit_chronicle):
        """Should record status change events."""
        entry = audit_chronicle.record_status_change(
            actor_id="CENTRAL-001",
            identity_ref="DID-abcd1234",
            previous_status="ACTIVE",
            new_status="SUSPENDED",
            reason="Test reason",
        )
        
        assert entry.event_type == AuditEventType.IDENTITY_STATUS_CHANGED
        assert entry.details["previous_status"] == "ACTIVE"
        assert entry.details["new_status"] == "SUSPENDED"
        assert entry.details["reason"] == "Test reason"
    
    def test_record_verification(self, audit_chronicle):
        """Should record verification events."""
        entry = audit_chronicle.record_verification(
            actor_id="HMRC-001",
            identity_ref="DID-abcd1234",
            verification_type="tax_period",
            result="CONTINUOUSLY_ACTIVE",
        )
        
        assert entry.event_type == AuditEventType.VERIFICATION_PERFORMED
        assert entry.details["verification_type"] == "tax_period"
        assert entry.details["result"] == "CONTINUOUSLY_ACTIVE"
    
    def test_record_authorisation_denied(self, audit_chronicle):
        """Should record authorisation denial events."""
        entry = audit_chronicle.record_authorisation_denied(
            actor_id="FAKE-ORG",
            attempted_operation="create_identity",
            reason="Not authorised",
        )
        
        assert entry.event_type == AuditEventType.AUTHORISATION_DENIED
        assert entry.outcome == "FAILURE"


class TestAuditRetrieval:
    """Tests for retrieving audit entries."""
    
    def test_get_entry_by_id(self, audit_chronicle):
        """Should retrieve entry by ID."""
        original = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
        )
        
        retrieved = audit_chronicle.get_entry(original.entry_id)
        
        assert retrieved is not None
        assert retrieved.entry_id == original.entry_id
    
    def test_get_nonexistent_entry_returns_none(self, audit_chronicle):
        """Should return None for nonexistent entry."""
        result = audit_chronicle.get_entry("AUD-NONEXISTENT")
        
        assert result is None
    
    def test_get_entries_for_identity(self, audit_chronicle):
        """Should retrieve all entries for an identity."""
        identity_ref = "DID-testid01"
        
        audit_chronicle.record_identity_creation("ACTOR", identity_ref, True)
        audit_chronicle.record_status_change("ACTOR", identity_ref, "ACTIVE", "SUSPENDED")
        audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
            identity_ref="DID-otherid",
        )
        
        entries = audit_chronicle.get_entries_for_identity(identity_ref)
        
        assert len(entries) == 2
        assert all(e.identity_ref == identity_ref for e in entries)
    
    def test_get_entries_by_event_type(self, audit_chronicle):
        """Should retrieve entries by event type."""
        audit_chronicle.record_identity_creation("ACTOR", "DID-1", True)
        audit_chronicle.record_identity_creation("ACTOR", "DID-2", True)
        audit_chronicle.record_verification("ACTOR", "DID-1", "basic", "VALID")
        
        entries = audit_chronicle.get_entries_by_event_type(
            AuditEventType.IDENTITY_CREATED
        )
        
        assert len(entries) == 2
        assert all(e.event_type == AuditEventType.IDENTITY_CREATED for e in entries)
    
    def test_get_entries_by_actor(self, audit_chronicle):
        """Should retrieve entries by actor."""
        audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR-A",
        )
        audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR-B",
        )
        audit_chronicle.record(
            event_type=AuditEventType.VERIFICATION_PERFORMED,
            actor_id="ACTOR-A",
        )
        
        entries = audit_chronicle.get_entries_by_actor("ACTOR-A")
        
        assert len(entries) == 2
        assert all(e.actor_id == "ACTOR-A" for e in entries)
    
    def test_get_recent_entries(self, audit_chronicle):
        """Should retrieve most recent entries."""
        for i in range(15):
            audit_chronicle.record(
                event_type=AuditEventType.IDENTITY_CREATED,
                actor_id=f"ACTOR-{i}",
            )
        
        recent = audit_chronicle.get_recent_entries(5)
        
        assert len(recent) == 5
    
    def test_get_all_entries(self, audit_chronicle):
        """Should retrieve all entries."""
        for i in range(5):
            audit_chronicle.record(
                event_type=AuditEventType.IDENTITY_CREATED,
                actor_id=f"ACTOR-{i}",
            )
        
        all_entries = audit_chronicle.get_all_entries()
        
        assert len(all_entries) == 5
    
    def test_count_entries(self, audit_chronicle):
        """Should count total entries."""
        for i in range(7):
            audit_chronicle.record(
                event_type=AuditEventType.IDENTITY_CREATED,
                actor_id="ACTOR",
            )
        
        assert audit_chronicle.count_entries() == 7


class TestAuditEntrySerialisation:
    """Tests for audit entry serialisation."""
    
    def test_entry_to_dict(self, audit_chronicle):
        """Should convert entry to dictionary."""
        entry = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
            identity_ref="DID-12345678",
            details={"key": "value"},
        )
        
        as_dict = entry.to_dict()
        
        assert as_dict["entry_id"] == entry.entry_id
        assert as_dict["event_type"] == "IDENTITY_CREATED"
        assert as_dict["actor_id"] == "ACTOR"
        assert as_dict["identity_ref"] == "DID-12345678"
        assert as_dict["details"]["key"] == "value"
    
    def test_entry_string_representation(self, audit_chronicle):
        """Should have readable string representation."""
        entry = audit_chronicle.record(
            event_type=AuditEventType.IDENTITY_CREATED,
            actor_id="ACTOR",
        )
        
        string_repr = str(entry)
        
        assert "IDENTITY_CREATED" in string_repr
        assert "ACTOR" in string_repr
