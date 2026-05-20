"""
Nexus Digital ID - Verification Module

Contains verification services for consuming organisations:
- PortalGateway: Routes verification requests to appropriate handlers
- BasicVerifier: Simple validity checks for employers/banks
- TaxVerifier: Period-based verification for tax authorities
- DVLAVerifier: Eligibility checks for driving licence authorities
"""

from nexus_digital_id.verification.portal_gateway import PortalGateway
from nexus_digital_id.verification.basic_verifier import BasicVerifier
from nexus_digital_id.verification.tax_verifier import TaxVerifier
from nexus_digital_id.verification.dvla_verifier import DVLAVerifier

__all__ = [
    "PortalGateway",
    "BasicVerifier",
    "TaxVerifier",
    "DVLAVerifier",
]
