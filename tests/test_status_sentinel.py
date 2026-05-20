"""
Nexus Digital ID - Status Sentinel Tests

Tests for identity status management and transitions.
"""

import pytest
from datetime import date

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    ImmutableAttributes,
    ModifiableAttributes,
    IdentityStatus,
)
from nexus_digital_id.core.status_sentinel import StatusSentinel
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    RevokedIdentityError,
    InvalidStatusTransitionError,
)


@pytest.fixture
def vault_with_identity():
    """Create a vault with a single active identity."""
    vault = DigitalIdentityVault()
    immutable = ImmutableAttributes(
        full_legal_name="Test Subject",
        date_of_birth=date(1990, 6, 15),
        place_of_birth="Bristol",
        nationality_at_birth="GBR",
    )
    modifiable = ModifiableAttributes(
        current_address="123 Test Street",
        contact_email="test@example.com",
        contact_phone="+447000000000",
        current_nationality="GBR",
    )
    record, _ = vault.store_identity(immutable, modifiable, "AUTH")
    return vault, record


class TestStatusTransitions:
    """Tests for valid status transitions."""
    
    def test_suspend_active_identity(self, vault_with_identity):
        """Should suspend an active identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        prev, new, changed = sentinel.suspend_identity(
            record.identity_ref, "AUTH", "Test suspension"
        )
        
        assert prev == IdentityStatus.ACTIVE
        assert new == IdentityStatus.SUSPENDED
        assert changed is True
    
    def test_reactivate_suspended_identity(self, vault_with_identity):
        """Should reactivate a suspended identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        prev, new, changed = sentinel.reactivate_identity(record.identity_ref, "AUTH")
        
        assert prev == IdentityStatus.SUSPENDED
        assert new == IdentityStatus.ACTIVE
        assert changed is True
    
    def test_revoke_active_identity(self, vault_with_identity):
        """Should revoke an active identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        prev, new, changed = sentinel.revoke_identity(
            record.identity_ref, "AUTH", "Fraud detected"
        )
        
        assert prev == IdentityStatus.ACTIVE
        assert new == IdentityStatus.REVOKED
        assert changed is True
    
    def test_revoke_suspended_identity(self, vault_with_identity):
        """Should revoke a suspended identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        prev, new, changed = sentinel.revoke_identity(record.identity_ref, "AUTH")
        
        assert prev == IdentityStatus.SUSPENDED
        assert new == IdentityStatus.REVOKED
        assert changed is True


class TestInvalidTransitions:
    """Tests for invalid status transitions."""
    
    def test_cannot_change_revoked_status(self, vault_with_identity):
        """Should not allow any changes to revoked identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.revoke_identity(record.identity_ref, "AUTH")
        
        with pytest.raises(RevokedIdentityError):
            sentinel.reactivate_identity(record.identity_ref, "AUTH")
    
    def test_cannot_suspend_revoked_identity(self, vault_with_identity):
        """Should not allow suspending a revoked identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.revoke_identity(record.identity_ref, "AUTH")
        
        with pytest.raises(RevokedIdentityError):
            sentinel.suspend_identity(record.identity_ref, "AUTH")
    
    def test_cannot_transition_to_same_status(self, vault_with_identity):
        """Should reject transition to current status."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        # Identity starts as ACTIVE
        with pytest.raises(InvalidStatusTransitionError):
            sentinel.transition_status(
                record.identity_ref, IdentityStatus.ACTIVE, "AUTH"
            )
    
    def test_cannot_reactivate_active_identity(self, vault_with_identity):
        """Should reject reactivating an already active identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        with pytest.raises(InvalidStatusTransitionError):
            sentinel.reactivate_identity(record.identity_ref, "AUTH")


class TestStatusQueries:
    """Tests for status query methods."""
    
    def test_get_current_status(self, vault_with_identity):
        """Should return current status."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        status = sentinel.get_current_status(record.identity_ref)
        
        assert status == IdentityStatus.ACTIVE
    
    def test_is_active_returns_true_for_active(self, vault_with_identity):
        """is_active should return True for active identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        assert sentinel.is_active(record.identity_ref) is True
    
    def test_is_suspended_returns_true_for_suspended(self, vault_with_identity):
        """is_suspended should return True for suspended identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        
        assert sentinel.is_suspended(record.identity_ref) is True
    
    def test_is_revoked_returns_true_for_revoked(self, vault_with_identity):
        """is_revoked should return True for revoked identity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.revoke_identity(record.identity_ref, "AUTH")
        
        assert sentinel.is_revoked(record.identity_ref) is True
    
    def test_can_transition_to_valid_status(self, vault_with_identity):
        """can_transition_to should return True for valid transitions."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        assert sentinel.can_transition_to(record.identity_ref, IdentityStatus.SUSPENDED) is True
        assert sentinel.can_transition_to(record.identity_ref, IdentityStatus.REVOKED) is True
    
    def test_can_transition_to_invalid_status(self, vault_with_identity):
        """can_transition_to should return False for invalid transitions."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        # Cannot transition to same status
        assert sentinel.can_transition_to(record.identity_ref, IdentityStatus.ACTIVE) is False


class TestStatusHistory:
    """Tests for status history tracking."""
    
    def test_status_history_records_transitions(self, vault_with_identity):
        """Status history should record all transitions."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "AUTH", "Reason 1")
        sentinel.reactivate_identity(record.identity_ref, "AUTH", "Reason 2")
        
        history = sentinel.get_status_history(record.identity_ref)
        
        # Initial creation + 2 transitions
        assert len(history) == 3
    
    def test_status_history_includes_reason(self, vault_with_identity):
        """Status history should include transition reason."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "AUTH", "Test reason")
        
        history = sentinel.get_status_history(record.identity_ref)
        last_entry = history[-1]
        
        assert last_entry.reason == "Test reason"
    
    def test_status_history_includes_authorising_entity(self, vault_with_identity):
        """Status history should include authorising entity."""
        vault, record = vault_with_identity
        sentinel = StatusSentinel(vault)
        
        sentinel.suspend_identity(record.identity_ref, "TEST-AUTH-001")
        
        history = sentinel.get_status_history(record.identity_ref)
        last_entry = history[-1]
        
        assert last_entry.authorising_entity == "TEST-AUTH-001"


class TestNonexistentIdentity:
    """Tests for operations on nonexistent identities."""
    
    def test_transition_nonexistent_raises_error(self, empty_vault):
        """Should raise error for nonexistent identity."""
        sentinel = StatusSentinel(empty_vault)
        
        with pytest.raises(IdentityNotFoundError):
            sentinel.transition_status(
                "DID-nonexist", IdentityStatus.SUSPENDED, "AUTH"
            )
    
    def test_get_status_nonexistent_raises_error(self, empty_vault):
        """Should raise error when getting status of nonexistent identity."""
        sentinel = StatusSentinel(empty_vault)
        
        with pytest.raises(IdentityNotFoundError):
            sentinel.get_current_status("DID-nonexist")
