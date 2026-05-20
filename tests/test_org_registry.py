"""
Tests for the Organisation Registry module.

Verifies organisation registration, access tier assignment,
retrieval, and lifecycle management.
"""

import pytest
from datetime import datetime

from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    OrganisationType,
    AccessTier,
)


class TestOrganisationRegistration:
    """Tests for organisation registration functionality."""

    def test_register_organisation_with_valid_data(self, org_registry):
        """Verify successful registration with all required fields."""
        org = org_registry.register_organisation(
            org_name="Acme Tax Services",
            org_type=OrganisationType.TAX_AUTHORITY,
        )
        
        assert org.org_name == "Acme Tax Services"
        assert org.org_type == OrganisationType.TAX_AUTHORITY
        assert org.org_id.startswith("TAX-")  # Tax authorities get TAX- prefix
        assert org.is_active is True
        assert isinstance(org.registration_timestamp, datetime)

    def test_register_organisation_with_explicit_tier(self, org_registry):
        """Verify registration with explicitly specified access tier."""
        org = org_registry.register_organisation(
            org_name="Premium Bank Ltd",
            org_type=OrganisationType.BANK,
            access_tier=AccessTier.ENHANCED,
        )
        
        assert org.access_tier == AccessTier.ENHANCED

    def test_register_organisation_default_tier_for_tax_authority(self, org_registry):
        """Verify tax authorities get ENHANCED tier by default."""
        org = org_registry.register_organisation(
            org_name="Revenue Services",
            org_type=OrganisationType.TAX_AUTHORITY,
        )
        
        assert org.access_tier == AccessTier.ENHANCED

    def test_register_organisation_default_tier_for_employer(self, org_registry):
        """Verify employers get BASIC tier by default."""
        org = org_registry.register_organisation(
            org_name="Tech Corp Ltd",
            org_type=OrganisationType.EMPLOYER,
        )
        
        assert org.access_tier == AccessTier.BASIC

    def test_register_organisation_default_tier_for_bank(self, org_registry):
        """Verify banks get BASIC tier by default."""
        org = org_registry.register_organisation(
            org_name="National Bank",
            org_type=OrganisationType.BANK,
        )
        
        assert org.access_tier == AccessTier.BASIC

    def test_register_organisation_default_tier_for_driving_licence(self, org_registry):
        """Verify driving licence authorities get ENHANCED tier by default."""
        org = org_registry.register_organisation(
            org_name="DVLA",
            org_type=OrganisationType.DRIVING_LICENCE_AUTHORITY,
        )
        
        assert org.access_tier == AccessTier.ENHANCED

    def test_register_organisation_default_tier_for_welfare(self, org_registry):
        """Verify welfare services get STANDARD tier by default."""
        org = org_registry.register_organisation(
            org_name="Social Services",
            org_type=OrganisationType.WELFARE_SERVICES,
        )
        
        assert org.access_tier == AccessTier.STANDARD

    def test_register_organisation_default_tier_for_immigration(self, org_registry):
        """Verify immigration bodies get ENHANCED tier by default."""
        org = org_registry.register_organisation(
            org_name="Border Agency",
            org_type=OrganisationType.IMMIGRATION,
        )
        
        assert org.access_tier == AccessTier.ENHANCED


class TestDuplicateOrganisationHandling:
    """Tests for duplicate organisation detection."""

    def test_duplicate_organisation_name_raises_error(self, org_registry):
        """Verify duplicate organisation names are rejected."""
        org_registry.register_organisation(
            org_name="Unique Corp",
            org_type=OrganisationType.EMPLOYER,
        )
        
        with pytest.raises(ValueError):
            org_registry.register_organisation(
                org_name="Unique Corp",
                org_type=OrganisationType.BANK,
            )

    def test_similar_names_are_allowed(self, org_registry):
        """Verify similar but different names are accepted."""
        org1 = org_registry.register_organisation(
            org_name="Acme Ltd",
            org_type=OrganisationType.EMPLOYER,
        )
        org2 = org_registry.register_organisation(
            org_name="Acme Limited",
            org_type=OrganisationType.EMPLOYER,
        )
        
        assert org1.org_id != org2.org_id


class TestOrganisationRetrieval:
    """Tests for organisation retrieval functionality."""

    def test_retrieve_organisation_by_id(self, org_registry):
        """Verify organisation can be retrieved by ID."""
        registered = org_registry.register_organisation(
            org_name="Findable Corp",
            org_type=OrganisationType.EMPLOYER,
        )
        
        retrieved = org_registry.get_organisation(registered.org_id)
        
        assert retrieved is not None
        assert retrieved.org_id == registered.org_id
        assert retrieved.org_name == "Findable Corp"

    def test_retrieve_nonexistent_organisation_returns_none(self, org_registry):
        """Verify None returned for unknown organisation ID."""
        result = org_registry.get_organisation("ORG-nonexistent")
        
        assert result is None

    def test_retrieve_central_authority(self, org_registry):
        """Verify Central Authority is always retrievable."""
        central = org_registry.get_organisation(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        
        assert central is not None
        assert central.org_name == OrganisationRegistry.CENTRAL_AUTHORITY_NAME
        assert central.access_tier == AccessTier.ENHANCED

    def test_organisation_exists_check(self, org_registry):
        """Verify existence check works correctly."""
        org = org_registry.register_organisation(
            org_name="Existing Corp",
            org_type=OrganisationType.EMPLOYER,
        )
        
        assert org_registry.is_registered(org.org_id) is True
        assert org_registry.is_registered("ORG-fake") is False


class TestOrganisationDeactivation:
    """Tests for organisation deactivation functionality."""

    def test_deactivate_organisation(self, org_registry):
        """Verify organisation can be deactivated."""
        org = org_registry.register_organisation(
            org_name="Soon Inactive Corp",
            org_type=OrganisationType.EMPLOYER,
        )
        
        result = org_registry.deactivate_organisation(org.org_id)
        
        assert result is True
        retrieved = org_registry.get_organisation(org.org_id)
        assert retrieved.is_active is False

    def test_deactivate_nonexistent_organisation(self, org_registry):
        """Verify deactivating unknown organisation returns False."""
        result = org_registry.deactivate_organisation("ORG-nonexistent")
        
        assert result is False

    def test_cannot_deactivate_central_authority(self, org_registry):
        """Verify Central Authority cannot be deactivated."""
        result = org_registry.deactivate_organisation(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        
        # Should either return False or raise an error
        central = org_registry.get_organisation(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        assert central.is_active is True


class TestOrganisationListing:
    """Tests for listing organisations."""

    def test_list_all_organisations(self, org_registry):
        """Verify all organisations are listed."""
        org_registry.register_organisation(
            org_name="Org One",
            org_type=OrganisationType.EMPLOYER,
        )
        org_registry.register_organisation(
            org_name="Org Two",
            org_type=OrganisationType.BANK,
        )
        
        all_orgs = org_registry.get_all_organisations()
        
        # Should include Central Authority plus the two registered
        assert len(all_orgs) >= 3

    def test_list_organisations_excludes_inactive_by_default(self, org_registry):
        """Verify inactive organisations are excluded by default."""
        org = org_registry.register_organisation(
            org_name="Will Be Inactive",
            org_type=OrganisationType.EMPLOYER,
        )
        org_registry.deactivate_organisation(org.org_id)
        
        active_orgs = org_registry.get_all_organisations(include_inactive=False)
        inactive_ids = [o.org_id for o in active_orgs if not o.is_active]
        
        assert org.org_id not in [o.org_id for o in active_orgs]

    def test_list_organisations_includes_inactive_when_requested(self, org_registry):
        """Verify inactive organisations included when requested."""
        org = org_registry.register_organisation(
            org_name="Inactive But Listed",
            org_type=OrganisationType.EMPLOYER,
        )
        org_registry.deactivate_organisation(org.org_id)
        
        all_orgs = org_registry.get_all_organisations(include_inactive=True)
        org_ids = [o.org_id for o in all_orgs]
        
        assert org.org_id in org_ids


class TestAccessTierValidation:
    """Tests for access tier validation and enforcement."""

    def test_is_central_authority_check(self, org_registry):
        """Verify Central Authority identification."""
        assert org_registry.is_central_authority(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        ) is True
        assert org_registry.is_central_authority("ORG-random") is False

    def test_get_access_tier_for_organisation(self, org_registry):
        """Verify access tier retrieval."""
        org = org_registry.register_organisation(
            org_name="Tiered Corp",
            org_type=OrganisationType.TAX_AUTHORITY,
            access_tier=AccessTier.STANDARD,
        )
        
        tier = org_registry.get_access_tier(org.org_id)
        
        assert tier == AccessTier.STANDARD

    def test_get_access_tier_for_unknown_organisation(self, org_registry):
        """Verify None returned for unknown organisation."""
        tier = org_registry.get_access_tier("ORG-unknown")
        
        assert tier is None


class TestOrganisationTypes:
    """Tests for organisation type enumeration."""

    def test_all_organisation_types_exist(self):
        """Verify all expected organisation types are defined."""
        expected_types = [
            "TAX_AUTHORITY",
            "DRIVING_LICENCE_AUTHORITY",
            "WELFARE_SERVICES",
            "IMMIGRATION",
            "LOCAL_AUTHORITY",
            "EMPLOYER",
            "BANK",
            "OTHER",
        ]
        
        for type_name in expected_types:
            assert hasattr(OrganisationType, type_name)

    def test_all_access_tiers_exist(self):
        """Verify all expected access tiers are defined."""
        expected_tiers = ["BASIC", "STANDARD", "ENHANCED"]
        
        for tier_name in expected_tiers:
            assert hasattr(AccessTier, tier_name)
