"""
Nexus Digital ID - Identity Vault Tests

Tests for the core identity storage and retrieval functionality.
"""

import pytest
from datetime import date

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityRecord,
    ImmutableAttributes,
    ModifiableAttributes,
    IdentityStatus,
    TemporaryRestriction,
)
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    ImmutableAttributeViolation,
)


class TestIdentityVaultCreation:
    """Tests for identity creation in the vault."""
    
    def test_store_new_identity_returns_record(
        self, empty_vault, sample_immutable_attrs, sample_modifiable_attrs
    ):
        """Storing a new identity should return the created record."""
        record, was_created = empty_vault.store_identity(
            immutable_attrs=sample_immutable_attrs,
            modifiable_attrs=sample_modifiable_attrs,
            creating_authority="NEXUS-CENTRAL-001",
        )
        
        assert was_created is True
        assert record is not None
        assert record.identity_ref.startswith("DID-")
        assert record.current_status == IdentityStatus.ACTIVE
    
    def test_store_identity_generates_unique_ref(
        self, empty_vault, sample_modifiable_attrs
    ):
        """Each new identity should have a unique reference."""
        attrs1 = ImmutableAttributes(
            full_legal_name="Person One",
            date_of_birth=date(1990, 1, 1),
            place_of_birth="London",
            nationality_at_birth="GBR",
        )
        attrs2 = ImmutableAttributes(
            full_legal_name="Person Two",
            date_of_birth=date(1991, 2, 2),
            place_of_birth="Paris",
            nationality_at_birth="FRA",
        )
        
        record1, _ = empty_vault.store_identity(attrs1, sample_modifiable_attrs, "AUTH")
        record2, _ = empty_vault.store_identity(attrs2, sample_modifiable_attrs, "AUTH")
        
        assert record1.identity_ref != record2.identity_ref
    
    def test_store_duplicate_identity_returns_existing(
        self, empty_vault, sample_immutable_attrs, sample_modifiable_attrs
    ):
        """Storing duplicate immutable attrs should return existing record."""
        record1, created1 = empty_vault.store_identity(
            sample_immutable_attrs, sample_modifiable_attrs, "AUTH"
        )
        record2, created2 = empty_vault.store_identity(
            sample_immutable_attrs, sample_modifiable_attrs, "AUTH"
        )
        
        assert created1 is True
        assert created2 is False
        assert record1.identity_ref == record2.identity_ref
    
    def test_new_identity_has_active_status(
        self, empty_vault, sample_immutable_attrs, sample_modifiable_attrs
    ):
        """New identities should have ACTIVE status."""
        record, _ = empty_vault.store_identity(
            sample_immutable_attrs, sample_modifiable_attrs, "AUTH"
        )
        
        assert record.current_status == IdentityStatus.ACTIVE
    
    def test_new_identity_has_creation_timestamp(
        self, empty_vault, sample_immutable_attrs, sample_modifiable_attrs
    ):
        """New identities should have a creation timestamp."""
        record, _ = empty_vault.store_identity(
            sample_immutable_attrs, sample_modifiable_attrs, "AUTH"
        )
        
        assert record.creation_timestamp is not None
    
    def test_new_identity_has_initial_status_history(
        self, empty_vault, sample_immutable_attrs, sample_modifiable_attrs
    ):
        """New identities should have initial status history entry."""
        record, _ = empty_vault.store_identity(
            sample_immutable_attrs, sample_modifiable_attrs, "AUTH"
        )
        
        assert len(record.status_history) == 1
        assert record.status_history[0].new_status == IdentityStatus.ACTIVE
        assert record.status_history[0].previous_status is None


class TestIdentityVaultRetrieval:
    """Tests for identity retrieval from the vault."""
    
    def test_retrieve_existing_identity(self, populated_vault):
        """Should retrieve an existing identity by reference."""
        vault, original = populated_vault
        
        retrieved = vault.retrieve_identity(original.identity_ref)
        
        assert retrieved.identity_ref == original.identity_ref
        assert retrieved.immutable_attrs.full_legal_name == original.immutable_attrs.full_legal_name
    
    def test_retrieve_nonexistent_identity_raises_error(self, empty_vault):
        """Should raise IdentityNotFoundError for unknown reference."""
        with pytest.raises(IdentityNotFoundError) as exc_info:
            empty_vault.retrieve_identity("DID-nonexist")
        
        assert "DID-nonexist" in str(exc_info.value)
    
    def test_identity_exists_returns_true_for_existing(self, populated_vault):
        """identity_exists should return True for existing identity."""
        vault, record = populated_vault
        
        assert vault.identity_exists(record.identity_ref) is True
    
    def test_identity_exists_returns_false_for_nonexistent(self, empty_vault):
        """identity_exists should return False for unknown reference."""
        assert empty_vault.identity_exists("DID-unknown") is False


class TestIdentityVaultAttributeUpdate:
    """Tests for attribute updates in the vault."""
    
    def test_update_modifiable_attribute_succeeds(self, populated_vault):
        """Should update a modifiable attribute."""
        vault, record = populated_vault
        
        old_val, new_val, changed = vault.update_modifiable_attribute(
            record.identity_ref,
            "current_address",
            "99 New Street, London",
        )
        
        assert changed is True
        assert new_val == "99 New Street, London"
    
    def test_update_same_value_returns_no_change(self, populated_vault):
        """Updating to same value should indicate no change."""
        vault, record = populated_vault
        current_address = record.modifiable_attrs.current_address
        
        old_val, new_val, changed = vault.update_modifiable_attribute(
            record.identity_ref,
            "current_address",
            current_address,
        )
        
        assert changed is False
        assert old_val == new_val
    
    def test_update_immutable_attribute_raises_error(self, populated_vault):
        """Should raise error when updating immutable attribute."""
        vault, record = populated_vault
        
        with pytest.raises(ImmutableAttributeViolation):
            vault.update_modifiable_attribute(
                record.identity_ref,
                "date_of_birth",
                "1990-01-01",
            )
    
    def test_update_nonexistent_identity_raises_error(self, empty_vault):
        """Should raise error when updating nonexistent identity."""
        with pytest.raises(IdentityNotFoundError):
            empty_vault.update_modifiable_attribute(
                "DID-nonexist",
                "current_address",
                "New Address",
            )


class TestTemporaryRestrictions:
    """Tests for temporary restriction management."""
    
    def test_add_restriction_to_identity(self, populated_vault):
        """Should add a temporary restriction."""
        vault, record = populated_vault
        
        restriction = TemporaryRestriction(
            restriction_type="DRIVING_MEDICAL",
            effective_date=date.today(),
            description="Medical review required",
        )
        
        vault.add_temporary_restriction(record.identity_ref, restriction)
        
        updated = vault.retrieve_identity(record.identity_ref)
        assert len(updated.temporary_restrictions) == 1
        assert updated.temporary_restrictions[0].restriction_type == "DRIVING_MEDICAL"
    
    def test_remove_restriction_from_identity(self, populated_vault):
        """Should remove a temporary restriction."""
        vault, record = populated_vault
        
        restriction = TemporaryRestriction(
            restriction_type="TRAVEL_BAN",
            effective_date=date.today(),
        )
        vault.add_temporary_restriction(record.identity_ref, restriction)
        
        removed = vault.remove_temporary_restriction(record.identity_ref, "TRAVEL_BAN")
        
        assert removed is True
        updated = vault.retrieve_identity(record.identity_ref)
        assert len(updated.temporary_restrictions) == 0
    
    def test_has_active_restrictions(self, populated_vault):
        """Should detect active restrictions."""
        vault, record = populated_vault
        
        restriction = TemporaryRestriction(
            restriction_type="TEST_RESTRICTION",
            effective_date=date.today(),
        )
        vault.add_temporary_restriction(record.identity_ref, restriction)
        
        updated = vault.retrieve_identity(record.identity_ref)
        assert updated.has_active_restrictions() is True


class TestImmutableAttributesFingerprint:
    """Tests for attribute fingerprinting."""
    
    def test_same_attributes_produce_same_fingerprint(self):
        """Identical attributes should produce identical fingerprint."""
        attrs1 = ImmutableAttributes(
            full_legal_name="Test Person",
            date_of_birth=date(1990, 5, 15),
            place_of_birth="London",
            nationality_at_birth="GBR",
        )
        attrs2 = ImmutableAttributes(
            full_legal_name="Test Person",
            date_of_birth=date(1990, 5, 15),
            place_of_birth="London",
            nationality_at_birth="GBR",
        )
        
        assert attrs1.compute_fingerprint() == attrs2.compute_fingerprint()
    
    def test_different_attributes_produce_different_fingerprint(self):
        """Different attributes should produce different fingerprint."""
        attrs1 = ImmutableAttributes(
            full_legal_name="Person One",
            date_of_birth=date(1990, 5, 15),
            place_of_birth="London",
            nationality_at_birth="GBR",
        )
        attrs2 = ImmutableAttributes(
            full_legal_name="Person Two",
            date_of_birth=date(1990, 5, 15),
            place_of_birth="London",
            nationality_at_birth="GBR",
        )
        
        assert attrs1.compute_fingerprint() != attrs2.compute_fingerprint()
