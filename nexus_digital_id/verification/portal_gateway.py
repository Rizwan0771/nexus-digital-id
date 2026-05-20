"""
Nexus Digital ID - Portal Gateway

Routes verification requests from consuming organisations to the
appropriate verification service based on organisation type and
access tier. Enforces authorisation before processing requests.
"""

from datetime import date
from typing import Optional, Union, Dict, Any

from nexus_digital_id.core.identity_vault import DigitalIdentityVault
from nexus_digital_id.authority.org_registry import (
    OrganisationRegistry,
    AccessTier,
    OrganisationType,
)
from nexus_digital_id.verification.basic_verifier import (
    BasicVerifier,
    BasicVerificationResult,
)
from nexus_digital_id.verification.tax_verifier import (
    TaxVerifier,
    TaxVerificationResult,
)
from nexus_digital_id.verification.dvla_verifier import (
    DVLAVerifier,
    DrivingEligibilityResult,
)
from nexus_digital_id.exceptions import (
    UnregisteredOrganisationError,
    InsufficientAccessTierError,
)


# Type alias for verification results
VerificationResult = Union[
    BasicVerificationResult,
    TaxVerificationResult,
    DrivingEligibilityResult,
]


class PortalGateway:
    """
    Central gateway for all verification requests from consuming organisations.
    
    Routes requests to appropriate verification services based on:
    - Organisation type (determines available verification types)
    - Access tier (determines level of information returned)
    
    Enforces authorisation before processing any request.
    """
    
    def __init__(
        self,
        identity_vault: DigitalIdentityVault,
        org_registry: OrganisationRegistry,
    ):
        """
        Initialise the Portal Gateway.
        
        Args:
            identity_vault: The vault containing identity records
            org_registry: Registry of consuming organisations
        """
        self._vault = identity_vault
        self._registry = org_registry
        
        # Initialise verification services
        self._basic_verifier = BasicVerifier(identity_vault)
        self._tax_verifier = TaxVerifier(identity_vault)
        self._dvla_verifier = DVLAVerifier(identity_vault)
    
    def _verify_organisation_access(
        self,
        org_id: str,
        required_operation: str,
    ) -> None:
        """
        Verify organisation is registered and authorised for the operation.
        
        Raises:
            UnregisteredOrganisationError: If organisation not registered
            InsufficientAccessTierError: If operation not permitted
        """
        if not self._registry.is_registered(org_id):
            raise UnregisteredOrganisationError()
        
        if not self._registry.is_active(org_id):
            raise UnregisteredOrganisationError()
        
        if not self._registry.can_perform_operation(org_id, required_operation):
            raise InsufficientAccessTierError()
    
    def verify_basic(
        self,
        identity_ref: str,
        requesting_org_id: str,
    ) -> BasicVerificationResult:
        """
        Perform a basic validity verification.
        
        Available to all registered organisations (BASIC tier and above).
        
        Args:
            identity_ref: The identity to verify
            requesting_org_id: ID of the requesting organisation
            
        Returns:
            BasicVerificationResult with validity status
            
        Raises:
            UnregisteredOrganisationError: If organisation not registered
        """
        self._verify_organisation_access(requesting_org_id, "verify_basic")
        return self._basic_verifier.verify_identity(identity_ref, requesting_org_id)
    
    def verify_for_tax_period(
        self,
        identity_ref: str,
        period_start: date,
        period_end: date,
        requesting_org_id: str,
    ) -> TaxVerificationResult:
        """
        Perform a tax authority verification for a reporting period.
        
        Available only to ENHANCED tier organisations with tax verification
        permissions (typically tax authorities like HMRC).
        
        Args:
            identity_ref: The identity to verify
            period_start: Start of the reporting period
            period_end: End of the reporting period
            requesting_org_id: ID of the tax authority
            
        Returns:
            TaxVerificationResult with period analysis
            
        Raises:
            UnregisteredOrganisationError: If organisation not registered
            InsufficientAccessTierError: If not authorised for tax verification
        """
        self._verify_organisation_access(requesting_org_id, "verify_tax_period")
        return self._tax_verifier.verify_for_period(
            identity_ref, period_start, period_end, requesting_org_id
        )
    
    def verify_driving_eligibility(
        self,
        identity_ref: str,
        requesting_org_id: str,
        check_date: Optional[date] = None,
    ) -> DrivingEligibilityResult:
        """
        Perform a driving licence eligibility verification.
        
        Available only to ENHANCED tier organisations with driving
        verification permissions (typically DVLA).
        
        Args:
            identity_ref: The identity to verify
            requesting_org_id: ID of the driving licence authority
            check_date: Date to check restrictions against
            
        Returns:
            DrivingEligibilityResult with eligibility status
            
        Raises:
            UnregisteredOrganisationError: If organisation not registered
            InsufficientAccessTierError: If not authorised for driving verification
        """
        self._verify_organisation_access(requesting_org_id, "verify_driving_eligibility")
        return self._dvla_verifier.verify_eligibility(
            identity_ref, requesting_org_id, check_date
        )
    
    def verify(
        self,
        identity_ref: str,
        requesting_org_id: str,
        verification_type: str = "basic",
        **kwargs,
    ) -> VerificationResult:
        """
        Unified verification endpoint that routes to appropriate service.
        
        Args:
            identity_ref: The identity to verify
            requesting_org_id: ID of the requesting organisation
            verification_type: Type of verification ("basic", "tax", "driving")
            **kwargs: Additional parameters for specific verification types
            
        Returns:
            Appropriate verification result based on type
            
        Raises:
            ValueError: If verification_type is not recognised
            UnregisteredOrganisationError: If organisation not registered
            InsufficientAccessTierError: If not authorised for requested type
        """
        if verification_type == "basic":
            return self.verify_basic(identity_ref, requesting_org_id)
        
        elif verification_type == "tax":
            period_start = kwargs.get("period_start")
            period_end = kwargs.get("period_end")
            if not period_start or not period_end:
                raise ValueError("Tax verification requires period_start and period_end")
            return self.verify_for_tax_period(
                identity_ref, period_start, period_end, requesting_org_id
            )
        
        elif verification_type == "driving":
            check_date = kwargs.get("check_date")
            return self.verify_driving_eligibility(
                identity_ref, requesting_org_id, check_date
            )
        
        else:
            raise ValueError(f"Unknown verification type: {verification_type}")
    
    def get_organisation_capabilities(self, org_id: str) -> Dict[str, Any]:
        """
        Get the verification capabilities available to an organisation.
        
        Returns information about what verification types the organisation
        can perform based on their access tier.
        """
        org = self._registry.get_organisation(org_id)
        if not org:
            raise UnregisteredOrganisationError()
        
        return {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "access_tier": org.access_tier.value,
            "available_verifications": {
                "basic": org.can_perform_operation("verify_basic"),
                "tax_period": org.can_perform_operation("verify_tax_period"),
                "driving_eligibility": org.can_perform_operation("verify_driving_eligibility"),
            },
            "permitted_operations": list(org.permitted_operations),
        }
