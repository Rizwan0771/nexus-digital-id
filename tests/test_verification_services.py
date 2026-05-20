"""
Nexus Digital ID - Verification Services Tests

Tests for the verification services used by consuming organisations.
"""

import pytest
from datetime import date, timedelta

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    ImmutableAttributes,
    ModifiableAttributes,
    IdentityStatus,
    TemporaryRestriction,
)
from nexus_digital_id.core.status_sentinel import StatusSentinel
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    OrganisationType,
    AccessTier,
)
from nexus_digital_id.verification.basic_verifier import (
    BasicVerifier,
    BasicVerificationOutcome,
)
from nexus_digital_id.verification.tax_verifier import (
    TaxVerifier,
    TaxVerificationOutcome,
)
from nexus_digital_id.verification.dvla_verifier import (
    DVLAVerifier,
    DrivingEligibilityOutcome,
)
from nexus_digital_id.verification.portal_gateway import PortalGateway
from nexus_digital_id.exceptions import (
    UnregisteredOrganisationError,
    InsufficientAccessTierError,
)


@pytest.fixture
def verification_setup():
    """Set up vault with identity and registry with organisations."""
    vault = DigitalIdentityVault()
    registry = OrganisationRegistry()
    
    # Create an identity
    immutable = ImmutableAttributes(
        full_legal_name="Verification Subject",
        date_of_birth=date(1988, 4, 12),
        place_of_birth="Cardiff",
        nationality_at_birth="GBR",
    )
    modifiable = ModifiableAttributes(
        current_address="55 Test Road, Cardiff",
        contact_email="verify@test.com",
        contact_phone="+447555555555",
        current_nationality="GBR",
    )
    record, _ = vault.store_identity(immutable, modifiable, "AUTH")
    
    # Register organisations
    hmrc = registry.register_organisation(
        org_name="HMRC",
        org_type=OrganisationType.TAX_AUTHORITY,
    )
    dvla = registry.register_organisation(
        org_name="DVLA",
        org_type=OrganisationType.DRIVING_LICENCE_AUTHORITY,
    )
    bank = registry.register_organisation(
        org_name="Test Bank",
        org_type=OrganisationType.BANK,
    )
    
    return {
        "vault": vault,
        "registry": registry,
        "record": record,
        "hmrc": hmrc,
        "dvla": dvla,
        "bank": bank,
    }


class TestBasicVerifier:
    """Tests for basic identity verification."""
    
    def test_verify_active_identity(self, verification_setup):
        """Should return VALID for active identity."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        bank = verification_setup["bank"]
        
        verifier = BasicVerifier(vault)
        result = verifier.verify_identity(record.identity_ref, bank.org_id)
        
        assert result.outcome == BasicVerificationOutcome.VALID
        assert result.is_currently_valid is True
    
    def test_verify_suspended_identity(self, verification_setup):
        """Should return SUSPENDED for suspended identity."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        bank = verification_setup["bank"]
        
        sentinel = StatusSentinel(vault)
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        
        verifier = BasicVerifier(vault)
        result = verifier.verify_identity(record.identity_ref, bank.org_id)
        
        assert result.outcome == BasicVerificationOutcome.SUSPENDED
        assert result.is_currently_valid is False
    
    def test_verify_revoked_identity(self, verification_setup):
        """Should return REVOKED for revoked identity."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        bank = verification_setup["bank"]
        
        sentinel = StatusSentinel(vault)
        sentinel.revoke_identity(record.identity_ref, "AUTH")
        
        verifier = BasicVerifier(vault)
        result = verifier.verify_identity(record.identity_ref, bank.org_id)
        
        assert result.outcome == BasicVerificationOutcome.REVOKED
        assert result.is_currently_valid is False
    
    def test_verify_nonexistent_identity(self, verification_setup):
        """Should return NOT_FOUND for nonexistent identity."""
        vault = verification_setup["vault"]
        bank = verification_setup["bank"]
        
        verifier = BasicVerifier(vault)
        result = verifier.verify_identity("DID-nonexist", bank.org_id)
        
        assert result.outcome == BasicVerificationOutcome.NOT_FOUND
        assert result.is_currently_valid is False


class TestTaxVerifier:
    """Tests for tax authority verification."""
    
    def test_verify_continuously_active(self, verification_setup):
        """Should return CONTINUOUSLY_ACTIVE for identity active throughout period."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        hmrc = verification_setup["hmrc"]
        
        verifier = TaxVerifier(vault)
        result = verifier.verify_for_period(
            record.identity_ref,
            date(2024, 4, 6),
            date(2025, 4, 5),
            hmrc.org_id,
        )
        
        assert result.outcome == TaxVerificationOutcome.CONTINUOUSLY_ACTIVE
        assert result.was_continuously_active is True
    
    def test_verify_with_suspension_during_period(self, verification_setup):
        """Should detect suspension during reporting period."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        hmrc = verification_setup["hmrc"]
        
        sentinel = StatusSentinel(vault)
        # Suspend and reactivate to create history
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        sentinel.reactivate_identity(record.identity_ref, "AUTH")
        
        verifier = TaxVerifier(vault)
        result = verifier.verify_for_period(
            record.identity_ref,
            date.today() - timedelta(days=30),
            date.today(),
            hmrc.org_id,
        )
        
        assert result.outcome == TaxVerificationOutcome.SUSPENSION_DETECTED
        assert result.was_continuously_active is False
    
    def test_verify_invalid_period_end_before_start(self, verification_setup):
        """Should return INVALID_PERIOD when end precedes start."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        hmrc = verification_setup["hmrc"]
        
        verifier = TaxVerifier(vault)
        result = verifier.verify_for_period(
            record.identity_ref,
            date(2025, 4, 5),  # End
            date(2024, 4, 6),  # Start (wrong order)
            hmrc.org_id,
        )
        
        assert result.outcome == TaxVerificationOutcome.INVALID_PERIOD
    
    def test_verify_nonexistent_identity(self, verification_setup):
        """Should return NOT_FOUND for nonexistent identity."""
        vault = verification_setup["vault"]
        hmrc = verification_setup["hmrc"]
        
        verifier = TaxVerifier(vault)
        result = verifier.verify_for_period(
            "DID-nonexist",
            date(2024, 4, 6),
            date(2025, 4, 5),
            hmrc.org_id,
        )
        
        assert result.outcome == TaxVerificationOutcome.NOT_FOUND


class TestDVLAVerifier:
    """Tests for driving licence eligibility verification."""
    
    def test_verify_eligible_identity(self, verification_setup):
        """Should return ELIGIBLE for active identity without restrictions."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        dvla = verification_setup["dvla"]
        
        verifier = DVLAVerifier(vault)
        result = verifier.verify_eligibility(record.identity_ref, dvla.org_id)
        
        assert result.outcome == DrivingEligibilityOutcome.ELIGIBLE
        assert result.is_eligible is True
        assert result.has_restrictions is False
    
    def test_verify_identity_with_restrictions(self, verification_setup):
        """Should return RESTRICTIONS_PRESENT for identity with active restrictions."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        dvla = verification_setup["dvla"]
        
        restriction = TemporaryRestriction(
            restriction_type="MEDICAL_REVIEW",
            effective_date=date.today() - timedelta(days=10),
            description="Medical review required",
        )
        vault.add_temporary_restriction(record.identity_ref, restriction)
        
        verifier = DVLAVerifier(vault)
        result = verifier.verify_eligibility(record.identity_ref, dvla.org_id)
        
        assert result.outcome == DrivingEligibilityOutcome.RESTRICTIONS_PRESENT
        assert result.is_eligible is False
        assert result.has_restrictions is True
    
    def test_verify_inactive_identity(self, verification_setup):
        """Should return IDENTITY_INACTIVE for suspended identity."""
        vault = verification_setup["vault"]
        record = verification_setup["record"]
        dvla = verification_setup["dvla"]
        
        sentinel = StatusSentinel(vault)
        sentinel.suspend_identity(record.identity_ref, "AUTH")
        
        verifier = DVLAVerifier(vault)
        result = verifier.verify_eligibility(record.identity_ref, dvla.org_id)
        
        assert result.outcome == DrivingEligibilityOutcome.IDENTITY_INACTIVE
        assert result.is_eligible is False
    
    def test_verify_nonexistent_identity(self, verification_setup):
        """Should return NOT_FOUND for nonexistent identity."""
        vault = verification_setup["vault"]
        dvla = verification_setup["dvla"]
        
        verifier = DVLAVerifier(vault)
        result = verifier.verify_eligibility("DID-nonexist", dvla.org_id)
        
        assert result.outcome == DrivingEligibilityOutcome.NOT_FOUND


class TestPortalGateway:
    """Tests for the verification portal gateway."""
    
    def test_basic_verification_via_gateway(self, verification_setup):
        """Should route basic verification correctly."""
        vault = verification_setup["vault"]
        registry = verification_setup["registry"]
        record = verification_setup["record"]
        bank = verification_setup["bank"]
        
        gateway = PortalGateway(vault, registry)
        result = gateway.verify_basic(record.identity_ref, bank.org_id)
        
        assert result.outcome == BasicVerificationOutcome.VALID
    
    def test_tax_verification_via_gateway(self, verification_setup):
        """Should route tax verification correctly."""
        vault = verification_setup["vault"]
        registry = verification_setup["registry"]
        record = verification_setup["record"]
        hmrc = verification_setup["hmrc"]
        
        gateway = PortalGateway(vault, registry)
        result = gateway.verify_for_tax_period(
            record.identity_ref,
            date(2024, 4, 6),
            date(2025, 4, 5),
            hmrc.org_id,
        )
        
        assert result.outcome == TaxVerificationOutcome.CONTINUOUSLY_ACTIVE
    
    def test_driving_verification_via_gateway(self, verification_setup):
        """Should route driving verification correctly."""
        vault = verification_setup["vault"]
        registry = verification_setup["registry"]
        record = verification_setup["record"]
        dvla = verification_setup["dvla"]
        
        gateway = PortalGateway(vault, registry)
        result = gateway.verify_driving_eligibility(record.identity_ref, dvla.org_id)
        
        assert result.outcome == DrivingEligibilityOutcome.ELIGIBLE
    
    def test_unregistered_organisation_rejected(self, verification_setup):
        """Should reject requests from unregistered organisations."""
        vault = verification_setup["vault"]
        registry = verification_setup["registry"]
        record = verification_setup["record"]
        
        gateway = PortalGateway(vault, registry)
        
        with pytest.raises(UnregisteredOrganisationError):
            gateway.verify_basic(record.identity_ref, "FAKE-ORG-001")
    
    def test_insufficient_access_tier_rejected(self, verification_setup):
        """Should reject requests outside organisation's access tier."""
        vault = verification_setup["vault"]
        registry = verification_setup["registry"]
        record = verification_setup["record"]
        bank = verification_setup["bank"]  # BASIC tier
        
        gateway = PortalGateway(vault, registry)
        
        # Bank (BASIC tier) should not be able to do tax verification
        with pytest.raises(InsufficientAccessTierError):
            gateway.verify_for_tax_period(
                record.identity_ref,
                date(2024, 4, 6),
                date(2025, 4, 5),
                bank.org_id,
            )
