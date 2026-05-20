"""
Nexus Digital ID - Basic Verifier

Provides simple validity verification for BASIC access tier organisations
such as employers and banks. Returns only whether an identity exists
and is currently active, without exposing any identity attributes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityStatus
from nexus_digital_id.exceptions import IdentityNotFoundError


class BasicVerificationOutcome(Enum):
    """Possible outcomes of a basic verification check."""
    VALID = "VALID"                     # ID exists and is ACTIVE
    NOT_FOUND = "NOT_FOUND"             # ID does not exist
    SUSPENDED = "SUSPENDED"             # ID exists but is suspended
    REVOKED = "REVOKED"                 # ID exists but has been revoked
    VERIFICATION_ERROR = "ERROR"        # System error during verification


@dataclass
class BasicVerificationResult:
    """
    Result of a basic identity verification.
    
    Contains only the verification outcome without any identity
    attributes, suitable for BASIC access tier organisations.
    """
    identity_ref: str
    outcome: BasicVerificationOutcome
    is_currently_valid: bool
    verification_timestamp: datetime
    requesting_org_id: str
    message: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialisation."""
        return {
            "identity_ref": self.identity_ref,
            "outcome": self.outcome.value,
            "is_currently_valid": self.is_currently_valid,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "requesting_org_id": self.requesting_org_id,
            "message": self.message,
        }


class BasicVerifier:
    """
    Verification service for BASIC access tier organisations.
    
    Provides simple yes/no validity checks without exposing
    any identity attributes or historical information.
    
    Suitable for:
    - Employers verifying employee identity
    - Banks verifying customer identity
    - Other organisations needing simple validity confirmation
    """
    
    def __init__(self, identity_vault: DigitalIdentityVault):
        """
        Initialise the Basic Verifier.
        
        Args:
            identity_vault: The vault containing identity records
        """
        self._vault = identity_vault
    
    def verify_identity(
        self,
        identity_ref: str,
        requesting_org_id: str,
    ) -> BasicVerificationResult:
        """
        Perform a basic validity check on a Digital Identity.
        
        Args:
            identity_ref: The identity to verify
            requesting_org_id: ID of the organisation making the request
            
        Returns:
            BasicVerificationResult with outcome and validity status
        """
        verification_time = datetime.utcnow()
        
        try:
            record = self._vault.retrieve_identity(identity_ref)
            
            if record.current_status == IdentityStatus.ACTIVE:
                return BasicVerificationResult(
                    identity_ref=identity_ref,
                    outcome=BasicVerificationOutcome.VALID,
                    is_currently_valid=True,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message="Identity is valid and currently active",
                )
            
            elif record.current_status == IdentityStatus.SUSPENDED:
                return BasicVerificationResult(
                    identity_ref=identity_ref,
                    outcome=BasicVerificationOutcome.SUSPENDED,
                    is_currently_valid=False,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message="Identity exists but is currently suspended",
                )
            
            else:  # REVOKED
                return BasicVerificationResult(
                    identity_ref=identity_ref,
                    outcome=BasicVerificationOutcome.REVOKED,
                    is_currently_valid=False,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message="Identity exists but has been permanently revoked",
                )
        
        except IdentityNotFoundError:
            return BasicVerificationResult(
                identity_ref=identity_ref,
                outcome=BasicVerificationOutcome.NOT_FOUND,
                is_currently_valid=False,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="No identity found with the specified reference",
            )
        
        except Exception:
            return BasicVerificationResult(
                identity_ref=identity_ref,
                outcome=BasicVerificationOutcome.VERIFICATION_ERROR,
                is_currently_valid=False,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="An error occurred during verification",
            )
    
    def is_valid(self, identity_ref: str, requesting_org_id: str) -> bool:
        """
        Quick check if an identity is currently valid.
        
        Convenience method that returns just a boolean.
        """
        result = self.verify_identity(identity_ref, requesting_org_id)
        return result.is_currently_valid
