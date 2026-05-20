"""
Tests for the Rule Enforcer module.

Verifies business rules enforcement including authority verification,
status restrictions, immutability constraints, and access level controls.
"""

import pytest
from datetime import date

from nexus_digital_id.compliance.rule_enforcer import (
    RuleEnforcer,
    RuleViolation,
    RuleCategory,
)
from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityStatus,
    ImmutableAttributes,
    ModifiableAttributes,
)
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    OrganisationType,
    AccessTier,
)
from nexus_digital_id.exceptions import (
    AuthorisationDeniedError,
    RevokedIdentityError,
    ImmutableAttributeViolation,
    InsufficientAccessTierError,
)


class TestAuthorityVerificationRules:
    """Tests for authority verification rules."""

    def test_central_authority_can_create_identity(self, rule_enforcer):
        """Verify Central Authority is authorised for creation."""
        violation = rule_enforcer.check_authority_for_creation(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        
        assert violation is None

    def test_consuming_organisation_cannot_create_identity(
        self, rule_enforcer, org_registry
    ):
        """Verify consuming organisations cannot create identities."""
        org = org_registry.register_organisation(
            org_name="Unauthorised Creator",
            org_type=OrganisationType.EMPLOYER,
        )
        
        violation = rule_enforcer.check_authority_for_creation(org.org_id)
        
        assert violation is not None
        assert violation.category == RuleCategory.AUTHORITY

    def test_central_authority_can_update_attributes(self, rule_enforcer):
        """Verify Central Authority can update attributes."""
        violation = rule_enforcer.check_authority_for_update(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        
        assert violation is None

    def test_consuming_organisation_cannot_update_attributes(
        self, rule_enforcer, org_registry
    ):
        """Verify consuming organisations cannot update attributes."""
        org = org_registry.register_organisation(
            org_name="Unauthorised Updater",
            org_type=OrganisationType.BANK,
        )
        
        violation = rule_enforcer.check_authority_for_update(org.org_id)
        
        assert violation is not None
        assert violation.category == RuleCategory.AUTHORITY

    def test_central_authority_can_change_status(self, rule_enforcer):
        """Verify Central Authority can change status."""
        violation = rule_enforcer.check_authority_for_status_change(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )
        
        assert violation is None

    def test_consuming_organisation_cannot_change_status(
        self, rule_enforcer, org_registry
    ):
        """Verify consuming organisations cannot change status."""
        org = org_registry.register_organisation(
            org_name="Unauthorised Status Changer",
            org_type=OrganisationType.TAX_AUTHORITY,
        )
        
        violation = rule_enforcer.check_authority_for_status_change(org.org_id)
        
        assert violation is not None
        assert violation.category == RuleCategory.AUTHORITY


class TestStatusRestrictionRules:
    """Tests for status-based restriction rules."""

    def test_active_identity_can_be_updated(
        self, rule_enforcer, sample_identity
    ):
        """Verify active identities can be updated."""
        violation = rule_enforcer.check_identity_not_revoked(
            sample_identity.identity_ref,
            "attribute_update",
        )
        
        assert violation is None

    def test_suspended_identity_can_be_updated(
        self, rule_enforcer, sample_identity, status_sentinel_for_sample
    ):
        """Verify suspended identities can be updated."""
        status_sentinel_for_sample.suspend_identity(
            sample_identity.identity_ref,
            "NEXUS-CENTRAL-001",
            "Test suspension",
        )
        
        violation = rule_enforcer.check_identity_not_revoked(
            sample_identity.identity_ref,
            "attribute_update",
        )
        
        assert violation is None

    def test_revoked_identity_cannot_be_updated(
        self, rule_enforcer, sample_identity, status_sentinel_for_sample
    ):
        """Verify revoked identities cannot be updated."""
        status_sentinel_for_sample.revoke_identity(
            sample_identity.identity_ref,
            "NEXUS-CENTRAL-001",
            "Test revocation",
        )
        
        violation = rule_enforcer.check_identity_not_revoked(
            sample_identity.identity_ref,
            "attribute_update",
        )
        
        assert violation is not None
        assert violation.category == RuleCategory.STATUS

    def test_revoked_identity_cannot_have_status_changed(
        self, rule_enforcer, sample_identity, status_sentinel_for_sample
    ):
        """Verify revoked identities cannot have status changed."""
        status_sentinel_for_sample.revoke_identity(
            sample_identity.identity_ref,
            "NEXUS-CENTRAL-001",
            "Test revocation",
        )
        
        violation = rule_enforcer.check_identity_not_revoked(
            sample_identity.identity_ref,
            "status_change",
        )
        
        assert violation is not None
        assert violation.category == RuleCategory.STATUS


class TestImmutableAttributeProtection:
    """Tests for immutable attribute protection rules."""

    def test_modifiable_attribute_can_be_updated(self, rule_enforcer):
        """Verify modifiable attributes can be updated."""
        modifiable_attrs = [
            "current_address",
            "contact_email",
            "contact_phone",
            "current_nationality",
        ]
        
        for attr in modifiable_attrs:
            violation = rule_enforcer.check_attribute_mutability(attr)
            assert violation is None, f"{attr} should be modifiable"

    def test_immutable_attribute_cannot_be_updated(self, rule_enforcer):
        """Verify immutable attributes cannot be updated."""
        immutable_attrs = [
            "full_legal_name",
            "date_of_birth",
            "place_of_birth",
            "nationality_at_birth",
        ]
        
        for attr in immutable_attrs:
            violation = rule_enforcer.check_attribute_mutability(attr)
            assert violation is not None, f"{attr} should be immutable"
            assert violation.category == RuleCategory.MUTABILITY

    def test_unknown_attribute_rejected(self, rule_enforcer):
        """Verify unknown attributes are rejected."""
        violation = rule_enforcer.check_attribute_mutability("nonexistent_field")
        
        assert violation is not None
        assert violation.category == RuleCategory.MUTABILITY


class TestAccessLevelEnforcement:
    """Tests for access level enforcement rules."""

    def test_basic_tier_can_perform_basic_verification(
        self, rule_enforcer, org_registry
    ):
        """Verify BASIC tier can perform basic verification."""
        org = org_registry.register_organisation(
            org_name="Basic Verifier",
            org_type=OrganisationType.EMPLOYER,
            access_tier=AccessTier.BASIC,
        )
        
        violation = rule_enforcer.check_access_tier_for_operation(
            org.org_id, "verify_basic"
        )
        
        assert violation is None

    def test_enhanced_tier_can_perform_all_verifications(
        self, rule_enforcer, org_registry
    ):
        """Verify ENHANCED tier can perform all verification types."""
        org = org_registry.register_organisation(
            org_name="Full Access Verifier",
            org_type=OrganisationType.WELFARE_SERVICES,
            access_tier=AccessTier.ENHANCED,
        )
        
        for operation in ["verify_basic", "verify_standard", "verify_enhanced"]:
            violation = rule_enforcer.check_access_tier_for_operation(
                org.org_id, operation
            )
            assert violation is None, f"ENHANCED should allow {operation}"


class TestEnforceCreationRules:
    """Tests for enforce_creation_rules method."""

    def test_enforce_creation_allows_central_authority(self, rule_enforcer):
        """Verify Central Authority passes creation enforcement."""
        # Should not raise
        rule_enforcer.enforce_creation_rules(
            OrganisationRegistry.CENTRAL_AUTHORITY_ID
        )

    def test_enforce_creation_blocks_consuming_org(
        self, rule_enforcer, org_registry
    ):
        """Verify consuming organisations are blocked from creation."""
        org = org_registry.register_organisation(
            org_name="Blocked Creator",
            org_type=OrganisationType.EMPLOYER,
        )
        
        with pytest.raises(AuthorisationDeniedError):
            rule_enforcer.enforce_creation_rules(org.org_id)


class TestEnforceUpdateRules:
    """Tests for enforce_update_rules method."""

    def test_enforce_update_allows_valid_request(
        self, rule_enforcer, sample_identity
    ):
        """Verify valid update request passes enforcement."""
        # Should not raise
        rule_enforcer.enforce_update_rules(
            actor_id=OrganisationRegistry.CENTRAL_AUTHORITY_ID,
            identity_ref=sample_identity.identity_ref,
            attribute_name="current_address",
        )

    def test_enforce_update_blocks_unauthorised_actor(
        self, rule_enforcer, org_registry, sample_identity
    ):
        """Verify unauthorised actors are blocked."""
        org = org_registry.register_organisation(
            org_name="Blocked Updater",
            org_type=OrganisationType.EMPLOYER,
        )
        
        with pytest.raises(AuthorisationDeniedError):
            rule_enforcer.enforce_update_rules(
                actor_id=org.org_id,
                identity_ref=sample_identity.identity_ref,
                attribute_name="current_address",
            )

    def test_enforce_update_blocks_revoked_identity(
        self, rule_enforcer, sample_identity, status_sentinel_for_sample
    ):
        """Verify updates to revoked identities are blocked."""
        status_sentinel_for_sample.revoke_identity(
            sample_identity.identity_ref,
            "NEXUS-CENTRAL-001",
            "Test",
        )
        
        with pytest.raises(RevokedIdentityError):
            rule_enforcer.enforce_update_rules(
                actor_id=OrganisationRegistry.CENTRAL_AUTHORITY_ID,
                identity_ref=sample_identity.identity_ref,
                attribute_name="current_address",
            )

    def test_enforce_update_blocks_immutable_attribute(
        self, rule_enforcer, sample_identity
    ):
        """Verify immutable attribute updates are blocked."""
        with pytest.raises(ImmutableAttributeViolation):
            rule_enforcer.enforce_update_rules(
                actor_id=OrganisationRegistry.CENTRAL_AUTHORITY_ID,
                identity_ref=sample_identity.identity_ref,
                attribute_name="date_of_birth",
            )


class TestEnforceVerificationRules:
    """Tests for enforce_verification_rules method."""

    def test_enforce_verification_allows_registered_org(
        self, rule_enforcer, org_registry
    ):
        """Verify registered organisations can perform verification."""
        org = org_registry.register_organisation(
            org_name="Registered Verifier",
            org_type=OrganisationType.EMPLOYER,
            access_tier=AccessTier.BASIC,
        )
        
        # Should not raise
        rule_enforcer.enforce_verification_rules(org.org_id, "verify_basic")

    def test_enforce_verification_blocks_unregistered_org(self, rule_enforcer):
        """Verify unregistered organisations are blocked."""
        with pytest.raises(AuthorisationDeniedError):
            rule_enforcer.enforce_verification_rules(
                "ORG-unregistered", "verify_basic"
            )


class TestValidateAllRules:
    """Tests for validate_all_rules method."""

    def test_validate_returns_empty_for_valid_request(
        self, rule_enforcer, sample_identity
    ):
        """Verify no violations for valid request."""
        violations = rule_enforcer.validate_all_rules(
            actor_id=OrganisationRegistry.CENTRAL_AUTHORITY_ID,
            operation="update_attribute",
            identity_ref=sample_identity.identity_ref,
            attribute_name="current_address",
        )
        
        assert len(violations) == 0

    def test_validate_returns_authority_violation(
        self, rule_enforcer, org_registry, sample_identity
    ):
        """Verify authority violations are returned."""
        org = org_registry.register_organisation(
            org_name="Violation Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        violations = rule_enforcer.validate_all_rules(
            actor_id=org.org_id,
            operation="update_attribute",
            identity_ref=sample_identity.identity_ref,
            attribute_name="current_address",
        )
        
        assert len(violations) > 0
        assert any(v.category == RuleCategory.AUTHORITY for v in violations)

    def test_validate_returns_multiple_violations(
        self, rule_enforcer, org_registry, sample_identity, status_sentinel_for_sample
    ):
        """Verify multiple violations are returned."""
        org = org_registry.register_organisation(
            org_name="Multi Violation Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        status_sentinel_for_sample.revoke_identity(
            sample_identity.identity_ref,
            "NEXUS-CENTRAL-001",
            "Test",
        )
        
        violations = rule_enforcer.validate_all_rules(
            actor_id=org.org_id,
            operation="update_attribute",
            identity_ref=sample_identity.identity_ref,
            attribute_name="date_of_birth",  # Immutable
        )
        
        # Should have authority, status, and mutability violations
        assert len(violations) >= 2


class TestRuleViolationDetails:
    """Tests for rule violation detail reporting."""

    def test_violation_includes_rule_name(self, rule_enforcer, org_registry):
        """Verify violations include rule names."""
        org = org_registry.register_organisation(
            org_name="Rule Name Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        violation = rule_enforcer.check_authority_for_creation(org.org_id)
        
        assert violation.rule_name is not None
        assert len(violation.rule_name) > 0

    def test_violation_includes_descriptive_message(
        self, rule_enforcer, org_registry
    ):
        """Verify violations include descriptive messages."""
        org = org_registry.register_organisation(
            org_name="Message Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        violation = rule_enforcer.check_authority_for_creation(org.org_id)
        
        assert violation.description is not None
        assert len(violation.description) > 10

    def test_violation_to_dict(self, rule_enforcer, org_registry):
        """Verify violation can be converted to dictionary."""
        org = org_registry.register_organisation(
            org_name="Dict Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        violation = rule_enforcer.check_authority_for_creation(org.org_id)
        violation_dict = violation.to_dict()
        
        assert "rule_name" in violation_dict
        assert "category" in violation_dict
        assert "description" in violation_dict


class TestDeterministicBehaviour:
    """Tests for deterministic rule evaluation."""

    def test_same_input_produces_same_result(
        self, rule_enforcer, org_registry, sample_identity
    ):
        """Verify identical inputs produce identical results."""
        org = org_registry.register_organisation(
            org_name="Deterministic Test",
            org_type=OrganisationType.EMPLOYER,
        )
        
        results = []
        for _ in range(5):
            violations = rule_enforcer.validate_all_rules(
                actor_id=org.org_id,
                operation="update_attribute",
                identity_ref=sample_identity.identity_ref,
                attribute_name="current_address",
            )
            results.append(len(violations))
        
        # All results should be identical
        assert all(r == results[0] for r in results)
