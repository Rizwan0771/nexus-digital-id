"""
Nexus Digital ID - Test Fixtures

Shared pytest fixtures for the test suite.
"""

import pytest
from datetime import date, datetime

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    ImmutableAttributes,
    ModifiableAttributes,
    IdentityStatus,
)
from nexus_digital_id.core.status_sentinel import StatusSentinel
from nexus_digital_id.core.attribute_keeper import AttributeKeeper
from nexus_digital_id.authority.central_command import CentralCommand
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    OrganisationType,
    AccessTier,
)
from nexus_digital_id.verification.portal_gateway import PortalGateway
from nexus_digital_id.compliance.audit_chronicle import AuditChronicle
from nexus_digital_id.compliance.request_sentinel import RequestSentinel
from nexus_digital_id.compliance.rule_enforcer import RuleEnforcer


@pytest.fixture
def empty_vault():
    """Provide an empty identity vault."""
    return DigitalIdentityVault()


@pytest.fixture
def sample_immutable_attrs():
    """Provide sample immutable attributes."""
    return ImmutableAttributes(
        full_legal_name="Eleanor Vance",
        date_of_birth=date(1985, 3, 22),
        place_of_birth="Manchester",
        nationality_at_birth="GBR",
    )


@pytest.fixture
def sample_modifiable_attrs():
    """Provide sample modifiable attributes."""
    return ModifiableAttributes(
        current_address="42 Willow Lane, Bristol BS1 4AB",
        contact_email="eleanor.vance@email.co.uk",
        contact_phone="+447700900123",
        current_nationality="GBR",
    )


@pytest.fixture
def populated_vault(empty_vault, sample_immutable_attrs, sample_modifiable_attrs):
    """Provide a vault with one identity."""
    record, _ = empty_vault.store_identity(
        immutable_attrs=sample_immutable_attrs,
        modifiable_attrs=sample_modifiable_attrs,
        creating_authority="NEXUS-CENTRAL-001",
    )
    return empty_vault, record


@pytest.fixture
def org_registry():
    """Provide an organisation registry."""
    return OrganisationRegistry()


@pytest.fixture
def central_command(empty_vault, org_registry):
    """Provide a CentralCommand instance."""
    return CentralCommand(empty_vault, org_registry)


@pytest.fixture
def status_sentinel(empty_vault):
    """Provide a StatusSentinel instance."""
    return StatusSentinel(empty_vault)


@pytest.fixture
def attribute_keeper(empty_vault):
    """Provide an AttributeKeeper instance."""
    return AttributeKeeper(empty_vault)


@pytest.fixture
def portal_gateway(empty_vault, org_registry):
    """Provide a PortalGateway instance."""
    return PortalGateway(empty_vault, org_registry)


@pytest.fixture
def audit_chronicle():
    """Provide an AuditChronicle instance."""
    return AuditChronicle()


@pytest.fixture
def request_sentinel():
    """Provide a RequestSentinel instance."""
    return RequestSentinel()


@pytest.fixture
def central_authority_id():
    """Provide the Central Authority ID."""
    return OrganisationRegistry.CENTRAL_AUTHORITY_ID


@pytest.fixture
def sample_creation_data():
    """Provide sample data for identity creation."""
    return {
        "full_legal_name": "James Thornbury",
        "date_of_birth": date(1988, 7, 15),
        "place_of_birth": "Birmingham",
        "nationality_at_birth": "GBR",
        "current_address": "17 Maple Grove, Leeds LS1 4AB",
        "contact_email": "j.thornbury@email.co.uk",
        "contact_phone": "+447891234567",
        "current_nationality": "GBR",
    }


@pytest.fixture
def identity_vault():
    """Provide an identity vault for tests that need shared state."""
    return DigitalIdentityVault()


@pytest.fixture
def sample_identity(identity_vault, sample_immutable_attrs, sample_modifiable_attrs):
    """Provide a sample identity record in the vault."""
    record, _ = identity_vault.store_identity(
        immutable_attrs=sample_immutable_attrs,
        modifiable_attrs=sample_modifiable_attrs,
        creating_authority="NEXUS-CENTRAL-001",
    )
    return record


@pytest.fixture
def status_sentinel_for_sample(identity_vault):
    """Provide a StatusSentinel that shares the same vault as sample_identity."""
    return StatusSentinel(identity_vault)


@pytest.fixture
def rule_enforcer(identity_vault, org_registry):
    """Provide a RuleEnforcer instance."""
    return RuleEnforcer(identity_vault, org_registry)
