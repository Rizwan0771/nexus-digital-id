"""
Nexus Digital ID - Central Command Tests

Tests for the main identity management interface.
"""

import pytest
from datetime import date

from nexus_digital_id.authority.central_command import CentralCommand
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    OrganisationType,
    AccessTier,
)
from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityStatus
from nexus_digital_id.exceptions import (
    AuthorisationDeniedError,
    IdentityNotFoundError,
    RevokedIdentityError,
    ImmutableAttributeViolation,
)


@pytest.fixture
def command_centre():
    """Create a CentralCommand instance."""
    vault = DigitalIdentityVault()
    registry = OrganisationRegistry()
    return CentralCommand(vault, registry)


@pytest.fixture
def command_with_identity(command_centre):
    """Create CentralCommand with one identity."""
    central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
    
    record, _ = command_centre.create_identity(
        requesting_org_id=central_id,
        full_legal_name="Test Person",
        date_of_birth=date(1990, 5, 15),
        place_of_birth="London",
        nationality_at_birth="GBR",
        current_address="123 Test Street",
        contact_email="test@example.com",
        contact_phone="+447000000000",
        current_nationality="GBR",
    )
    
    return command_centre, record


class TestIdentityCreation:
    """Tests for identity creation via Central Command."""
    
    def test_central_authority_can_create_identity(self, command_centre):
        """Central Authority should be able to create identities."""
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        record, was_created = command_centre.create_identity(
            requesting_org_id=central_id,
            full_legal_name="New Person",
            date_of_birth=date(1985, 3, 22),
            place_of_birth="Manchester",
            nationality_at_birth="GBR",
            current_address="42 Willow Lane",
            contact_email="new@example.com",
            contact_phone="+447111111111",
            current_nationality="GBR",
        )
        
        assert was_created is True
        assert record.identity_ref.startswith("DID-")
        assert record.current_status == IdentityStatus.ACTIVE
    
    def test_non_central_authority_cannot_create_identity(self, command_centre):
        """Non-Central Authority should not be able to create identities."""
        # Register a consuming organisation
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        org = command_centre.register_organisation(
            requesting_org_id=central_id,
            org_name="Test Bank",
            org_type=OrganisationType.BANK,
        )
        
        with pytest.raises(AuthorisationDeniedError):
            command_centre.create_identity(
                requesting_org_id=org.org_id,
                full_legal_name="Unauthorised Creation",
                date_of_birth=date(1990, 1, 1),
                place_of_birth="London",
                nationality_at_birth="GBR",
                current_address="Address",
                contact_email="email@test.com",
                contact_phone="+447000000000",
                current_nationality="GBR",
            )
    
    def test_idempotent_creation(self, command_centre):
        """Creating same identity twice should return existing record."""
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        record1, created1 = command_centre.create_identity(
            requesting_org_id=central_id,
            full_legal_name="Duplicate Test",
            date_of_birth=date(1988, 7, 15),
            place_of_birth="Birmingham",
            nationality_at_birth="GBR",
            current_address="Address",
            contact_email="dup@test.com",
            contact_phone="+447222222222",
            current_nationality="GBR",
        )
        
        record2, created2 = command_centre.create_identity(
            requesting_org_id=central_id,
            full_legal_name="Duplicate Test",
            date_of_birth=date(1988, 7, 15),
            place_of_birth="Birmingham",
            nationality_at_birth="GBR",
            current_address="Different Address",
            contact_email="different@test.com",
            contact_phone="+447333333333",
            current_nationality="GBR",
        )
        
        assert created1 is True
        assert created2 is False
        assert record1.identity_ref == record2.identity_ref


class TestAttributeUpdates:
    """Tests for attribute updates via Central Command."""
    
    def test_update_modifiable_attribute(self, command_with_identity):
        """Should update a modifiable attribute."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        old_val, new_val, changed = command.update_attribute(
            requesting_org_id=central_id,
            identity_ref=record.identity_ref,
            attribute_name="current_address",
            new_value="999 New Address",
        )
        
        assert changed is True
        assert new_val == "999 New Address"
    
    def test_cannot_update_immutable_attribute(self, command_with_identity):
        """Should not allow updating immutable attributes."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        with pytest.raises(ImmutableAttributeViolation):
            command.update_attribute(
                requesting_org_id=central_id,
                identity_ref=record.identity_ref,
                attribute_name="date_of_birth",
                new_value="1995-01-01",
            )
    
    def test_cannot_update_revoked_identity(self, command_with_identity):
        """Should not allow updating revoked identity."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        command.revoke_identity(central_id, record.identity_ref)
        
        with pytest.raises(RevokedIdentityError):
            command.update_attribute(
                requesting_org_id=central_id,
                identity_ref=record.identity_ref,
                attribute_name="current_address",
                new_value="New Address",
            )


class TestStatusManagement:
    """Tests for status management via Central Command."""
    
    def test_suspend_identity(self, command_with_identity):
        """Should suspend an active identity."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        prev, new, changed = command.suspend_identity(
            central_id, record.identity_ref, "Test suspension"
        )
        
        assert prev == IdentityStatus.ACTIVE
        assert new == IdentityStatus.SUSPENDED
        assert changed is True
    
    def test_reactivate_identity(self, command_with_identity):
        """Should reactivate a suspended identity."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        command.suspend_identity(central_id, record.identity_ref)
        prev, new, changed = command.reactivate_identity(
            central_id, record.identity_ref
        )
        
        assert prev == IdentityStatus.SUSPENDED
        assert new == IdentityStatus.ACTIVE
    
    def test_revoke_identity(self, command_with_identity):
        """Should permanently revoke an identity."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        prev, new, changed = command.revoke_identity(
            central_id, record.identity_ref, "Fraud"
        )
        
        assert new == IdentityStatus.REVOKED


class TestOrganisationManagement:
    """Tests for organisation registration via Central Command."""
    
    def test_register_organisation(self, command_centre):
        """Should register a new organisation."""
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        org = command_centre.register_organisation(
            requesting_org_id=central_id,
            org_name="Test Tax Authority",
            org_type=OrganisationType.TAX_AUTHORITY,
        )
        
        assert org.org_name == "Test Tax Authority"
        assert org.org_type == OrganisationType.TAX_AUTHORITY
        assert org.access_tier == AccessTier.ENHANCED
    
    def test_register_organisation_with_custom_tier(self, command_centre):
        """Should register organisation with specified tier."""
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        org = command_centre.register_organisation(
            requesting_org_id=central_id,
            org_name="Custom Tier Org",
            org_type=OrganisationType.OTHER,
            access_tier=AccessTier.STANDARD,
        )
        
        assert org.access_tier == AccessTier.STANDARD
    
    def test_deactivate_organisation(self, command_centre):
        """Should deactivate an organisation."""
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        org = command_centre.register_organisation(
            requesting_org_id=central_id,
            org_name="To Deactivate",
            org_type=OrganisationType.EMPLOYER,
        )
        
        result = command_centre.deactivate_organisation(central_id, org.org_id)
        
        assert result is True


class TestSystemStatistics:
    """Tests for system statistics."""
    
    def test_get_statistics_empty_system(self, command_centre):
        """Should return statistics for empty system."""
        stats = command_centre.get_system_statistics()
        
        assert stats["total_identities"] == 0
        assert stats["total_organisations"] == 1  # Central Authority
    
    def test_get_statistics_with_data(self, command_with_identity):
        """Should return accurate statistics."""
        command, record = command_with_identity
        central_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        
        # Add another identity and suspend it
        record2, _ = command.create_identity(
            requesting_org_id=central_id,
            full_legal_name="Second Person",
            date_of_birth=date(1992, 8, 20),
            place_of_birth="Leeds",
            nationality_at_birth="GBR",
            current_address="456 Other Street",
            contact_email="second@test.com",
            contact_phone="+447444444444",
            current_nationality="GBR",
        )
        command.suspend_identity(central_id, record2.identity_ref)
        
        stats = command.get_system_statistics()
        
        assert stats["total_identities"] == 2
        assert stats["identities_by_status"]["ACTIVE"] == 1
        assert stats["identities_by_status"]["SUSPENDED"] == 1
