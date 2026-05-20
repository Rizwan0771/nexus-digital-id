"""
Nexus Digital ID - Tax Authority Verifier

Provides period-based verification for tax authorities (e.g., HMRC).
Checks not only current validity but also whether the identity was
suspended at any point during a specified reporting period.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum

from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityStatus
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    InvalidReportingPeriodError,
)


class TaxVerificationOutcome(Enum):
    """Possible outcomes of a tax authority verification."""
    CONTINUOUSLY_ACTIVE = "CONTINUOUSLY_ACTIVE"     # Active throughout period
    SUSPENSION_DETECTED = "SUSPENSION_DETECTED"     # Had suspension during period
    CURRENTLY_INACTIVE = "CURRENTLY_INACTIVE"       # Not currently active
    NOT_FOUND = "NOT_FOUND"                         # ID does not exist
    INVALID_PERIOD = "INVALID_PERIOD"               # Invalid reporting period
    VERIFICATION_ERROR = "ERROR"                    # System error


@dataclass
class TaxVerificationResult:
    """
    Result of a tax authority verification.
    
    Includes information about the reporting period and any
    suspension periods that overlap with it.
    """
    identity_ref: str
    outcome: TaxVerificationOutcome
    is_currently_active: bool
    was_continuously_active: bool
    reporting_period_start: Optional[date]
    reporting_period_end: Optional[date]
    suspension_periods: List[Dict[str, str]] = field(default_factory=list)
    verification_timestamp: datetime = field(default_factory=datetime.utcnow)
    requesting_org_id: str = ""
    message: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialisation."""
        return {
            "identity_ref": self.identity_ref,
            "outcome": self.outcome.value,
            "is_currently_active": self.is_currently_active,
            "was_continuously_active": self.was_continuously_active,
            "reporting_period": {
                "start": self.reporting_period_start.isoformat() if self.reporting_period_start else None,
                "end": self.reporting_period_end.isoformat() if self.reporting_period_end else None,
            },
            "suspension_periods": self.suspension_periods,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "requesting_org_id": self.requesting_org_id,
            "message": self.message,
        }


class TaxVerifier:
    """
    Verification service for tax authorities.
    
    Provides enhanced verification that checks:
    1. Whether the identity exists
    2. Whether the identity is currently active
    3. Whether the identity was suspended at any point during
       a specified reporting period
    
    This is essential for tax authorities to validate that an
    individual was eligible throughout a tax year or reporting period.
    """
    
    def __init__(self, identity_vault: DigitalIdentityVault):
        """
        Initialise the Tax Verifier.
        
        Args:
            identity_vault: The vault containing identity records
        """
        self._vault = identity_vault
    
    def verify_for_period(
        self,
        identity_ref: str,
        period_start: date,
        period_end: date,
        requesting_org_id: str,
    ) -> TaxVerificationResult:
        """
        Verify an identity for a specific reporting period.
        
        Args:
            identity_ref: The identity to verify
            period_start: Start of the reporting period
            period_end: End of the reporting period
            requesting_org_id: ID of the tax authority making the request
            
        Returns:
            TaxVerificationResult with detailed period analysis
        """
        verification_time = datetime.utcnow()
        
        # Validate reporting period
        if period_start is None or period_end is None:
            return TaxVerificationResult(
                identity_ref=identity_ref,
                outcome=TaxVerificationOutcome.INVALID_PERIOD,
                is_currently_active=False,
                was_continuously_active=False,
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="Reporting period must specify both start and end dates",
            )
        
        if period_end < period_start:
            return TaxVerificationResult(
                identity_ref=identity_ref,
                outcome=TaxVerificationOutcome.INVALID_PERIOD,
                is_currently_active=False,
                was_continuously_active=False,
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="Reporting period end date cannot precede start date",
            )
        
        try:
            record = self._vault.retrieve_identity(identity_ref)
            
            is_currently_active = record.current_status == IdentityStatus.ACTIVE
            
            # Check for suspensions during the period
            had_suspension, suspension_periods = record.was_suspended_during_period(
                period_start, period_end
            )
            
            # Determine outcome
            if not is_currently_active:
                return TaxVerificationResult(
                    identity_ref=identity_ref,
                    outcome=TaxVerificationOutcome.CURRENTLY_INACTIVE,
                    is_currently_active=False,
                    was_continuously_active=False,
                    reporting_period_start=period_start,
                    reporting_period_end=period_end,
                    suspension_periods=suspension_periods,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message=f"Identity is currently {record.current_status.value}",
                )
            
            if had_suspension:
                return TaxVerificationResult(
                    identity_ref=identity_ref,
                    outcome=TaxVerificationOutcome.SUSPENSION_DETECTED,
                    is_currently_active=True,
                    was_continuously_active=False,
                    reporting_period_start=period_start,
                    reporting_period_end=period_end,
                    suspension_periods=suspension_periods,
                    verification_timestamp=verification_time,
                    requesting_org_id=requesting_org_id,
                    message="Identity had suspension period(s) during the reporting period",
                )
            
            return TaxVerificationResult(
                identity_ref=identity_ref,
                outcome=TaxVerificationOutcome.CONTINUOUSLY_ACTIVE,
                is_currently_active=True,
                was_continuously_active=True,
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="Identity was continuously active throughout the reporting period",
            )
        
        except IdentityNotFoundError:
            return TaxVerificationResult(
                identity_ref=identity_ref,
                outcome=TaxVerificationOutcome.NOT_FOUND,
                is_currently_active=False,
                was_continuously_active=False,
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="No identity found with the specified reference",
            )
        
        except Exception:
            return TaxVerificationResult(
                identity_ref=identity_ref,
                outcome=TaxVerificationOutcome.VERIFICATION_ERROR,
                is_currently_active=False,
                was_continuously_active=False,
                reporting_period_start=period_start,
                reporting_period_end=period_end,
                verification_timestamp=verification_time,
                requesting_org_id=requesting_org_id,
                message="An error occurred during verification",
            )
    
    def was_continuously_active(
        self,
        identity_ref: str,
        period_start: date,
        period_end: date,
        requesting_org_id: str,
    ) -> bool:
        """
        Quick check if identity was continuously active during period.
        
        Convenience method that returns just a boolean.
        """
        result = self.verify_for_period(
            identity_ref, period_start, period_end, requesting_org_id
        )
        return result.was_continuously_active
