"""
Nexus Digital ID - DVLA Verifier

Provides eligibility verification for driving licence authorities.
Checks identity validity and temporary restrictions that may affect
driving licence issuance or renewal.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from enum import Enum

from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityStatus
from nexus_digital_id.exceptions import IdentityNotFoundError


class DrivingEligibilityOutcome(Enum):
    """Possible outcomes of a driving eligibility check."""
    ELIGIBLE = "ELIGIBLE"                       # Active with no restrictions
    RESTRICTIONS_PRESENT = "RESTRICTIONS"       # Active but has restrictions
    IDENTITY_INACTIVE = "INACTIVE"              # Not currently active
    NOT_FOUND = "NOT_FOUND"                     # ID does not exist
    VERIFICATION_ERROR = "ERROR"                # System error


@dataclass
class DrivingEligibilityResult:
    """
    Result of a driving licence eligibility verification.
    
    Indicates whether the individual is eligible for licence
    issuance/renewal without disclosing specific restriction details.
    """
    identity_ref: str
    outcome: DrivingEligibilityOutcome
    is_eligible: bool
    has_restrictions: bool
    restriction_count: int
    verification_timestamp: datetime
    requesting_org_id: str
    message: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialisation."""
        return {
            "identity_ref": self.identity_ref,
            "outcome": self.outcome.value,
            "is_eligible": self.is_eligible,
            "has_restrictions": self.has_restrictions,
            "restriction_count": self.restriction_count,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "requesting_org_id": self.requesting_org_id,
            "message": self.message,
        }


class DVLAVerifier:
    """
    Verification service for driving licence authorities.
    
    Provides eligibility checks that verify:
    1. Whether the identity exists and is currently active
    2. Whether there are any temporary restrictions that would
       affect driving licence issuance or renewal
    
    Restriction details are not disclosed - only their presence
    is indicated to protect individual privacy.
    """
    
    def __init__(self, identity_vault: DigitalIdentityVault):
        """
        Initialise the DVLA Verifier.
        
        Args:
            identity_vault: The vault containing identity records
        """
        self._vault = identity_vault
    
    def verify_eligibility(
        self,
        identity_ref: str,
        requesting_org_id: str,
        check_date: Optional[date] = None,
    ) -> DrivingEligibilityResult:
        """
        Verify driving licence eligibility for an identity.
        
        Args:
            identity_ref: The identity to verify
            requesting_org_id: ID of the DVLA making the request
            check_date: Date to check restrictions against (defaults to today)
            
        Returns:
            DrivingEligibilityResult with eligibility status
        """
        verification_time = datetime.utcnow()
        check_date = check_date or date.today()
        
        try:
            record = self._vault.retrieve_identity(identity_ref)
            
            # First check if identity is active
            if record.current_status != IdentityStatus.ACTIVE:
                return DrivingEligibilityResult(
                    identity_ref=identity_ref,
                    outcome=DrivingEligibilityOutcome.IDENTITY_INACTIVE,
                    is_eligible=False,
                    has_restrictions=False,
                    restriction_count=0,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message=f"Identity is not currently active (status: {record.current_status.value})",
                )
            
            # Check for active restrictions
            active_restrictions = record.get_active_restrictions(check_date)
            has_restrictions = len(active_restrictions) > 0
            
            if has_restrictions:
                return DrivingEligibilityResult(
                    identity_ref=identity_ref,
                    outcome=DrivingEligibilityOutcome.RESTRICTIONS_PRESENT,
                    is_eligible=False,
                    has_restrictions=True,
                    restriction_count=len(active_restrictions),
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message="Identity has active restrictions affecting eligibility",
                )
            
            return DrivingEligibilityResult(
                identity_ref=identity_ref,
                outcome=DrivingEligibilityOutcome.ELIGIBLE,
                is_eligible=True,
                has_restrictions=False,
                restriction_count=0,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="Identity is eligible for driving licence issuance/renewal",
            )
        
        except IdentityNotFoundError:
            return DrivingEligibilityResult(
                identity_ref=identity_ref,
                outcome=DrivingEligibilityOutcome.NOT_FOUND,
                is_eligible=False,
                has_restrictions=False,
                restriction_count=0,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="No identity found with the specified reference",
            )
        
        except Exception:
            return DrivingEligibilityResult(
                identity_ref=identity_ref,
                outcome=DrivingEligibilityOutcome.VERIFICATION_ERROR,
                is_eligible=False,
                has_restrictions=False,
                restriction_count=0,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="An error occurred during verification",
            )
    
    def is_eligible(
        self,
        identity_ref: str,
        requesting_org_id: str,
        check_date: Optional[date] = None,
    ) -> bool:
        """
        Quick check if identity is eligible for driving licence.
        
        Convenience method that returns just a boolean.
        """
        result = self.verify_eligibility(identity_ref, requesting_org_id, check_date)
        return result.is_eligible
