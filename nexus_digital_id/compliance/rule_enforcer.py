"""
Nexus Digital ID - Rule Enforcer

Business rules engine that enforces system-wide constraints
and policies consistently across all operations.

Rule Precedence (evaluated in order):
1. Authority verification (is actor authorised?)
2. Digital ID status restrictions (is ID revoked?)
3. Attribute mutability constraints (is attribute immutable?)
4. Access level restrictions (does org have required tier?)
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from nexus_digital_id.core.identity_vault import DigitalIdentityVault, IdentityStatus
from nexus_digital_id.core.attribute_keeper import AttributeKeeper
from nexus_digital_id.authority.org_registry import OrganisationRegistry, AccessTier
from nexus_digital_id.exceptions import (
    BusinessRuleViolationError,
    AuthorisationDeniedError,
    RevokedIdentityError,
    ImmutableAttributeViolation,
    InsufficientAccessTierError,
    IdentityNotFoundError,
)


class RuleCategory(Enum):
    """Categories of business rules."""
    AUTHORITY = "AUTHORITY"
    STATUS = "STATUS"
    MUTABILITY = "MUTABILITY"
    ACCESS_LEVEL = "ACCESS_LEVEL"


@dataclass
class RuleViolation:
    """Details of a business rule violation."""
    rule_name: str
    category: RuleCategory
    description: str
    
    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "category": self.category.value,
            "description": self.description,
        }


class RuleEnforcer:
    """
    Central business rules engine for the Digital ID system.
    
    Enforces the following rules:
    
    1. AUTHORITY RULES:
       - Only Central Authority can create identities
       - Only Central Authority can update attributes
       - Only Central Authority can change status
       - Only Central Authority can manage restrictions
    
    2. STATUS RULES:
       - Revoked identities cannot be updated
       - Revoked identities cannot have status changed
       - Status transitions must follow valid paths
    
    3. MUTABILITY RULES:
       - Immutable attributes cannot be modified after creation
       - Only defined modifiable attributes can be updated
    
    4. ACCESS LEVEL RULES:
       - Organisations can only perform operations within their tier
       - Enhanced operations require ENHANCED access tier
    """
    
    def __init__(
        self,
        identity_vault: DigitalIdentityVault,
        org_registry: OrganisationRegistry,
    ):
        """
        Initialise the Rule Enforcer.
        
        Args:
            identity_vault: The vault containing identity records
            org_registry: Registry of organisations
        """
        self._vault = identity_vault
        self._registry = org_registry
    
    def check_authority_for_creation(self, actor_id: str) -> Optional[RuleViolation]:
        """Check if actor is authorised to create identities."""
        if not self._registry.is_central_authority(actor_id):
            return RuleViolation(
                rule_name="CENTRAL_AUTHORITY_ONLY_CREATE",
                category=RuleCategory.AUTHORITY,
                description="Only the Central Authority can create Digital Identities",
            )
        return None
    
    def check_authority_for_update(self, actor_id: str) -> Optional[RuleViolation]:
        """Check if actor is authorised to update identities."""
        if not self._registry.is_central_authority(actor_id):
            return RuleViolation(
                rule_name="CENTRAL_AUTHORITY_ONLY_UPDATE",
                category=RuleCategory.AUTHORITY,
                description="Only the Central Authority can update Digital Identity attributes",
            )
        return None
    
    def check_authority_for_status_change(self, actor_id: str) -> Optional[RuleViolation]:
        """Check if actor is authorised to change identity status."""
        if not self._registry.is_central_authority(actor_id):
            return RuleViolation(
                rule_name="CENTRAL_AUTHORITY_ONLY_STATUS",
                category=RuleCategory.AUTHORITY,
                description="Only the Central Authority can change Digital Identity status",
            )
        return None
    
    def check_identity_not_revoked(
        self,
        identity_ref: str,
        operation: str,
    ) -> Optional[RuleViolation]:
        """Check if identity is revoked (which blocks most operations)."""
        try:
            record = self._vault.retrieve_identity(identity_ref)
            if record.current_status == IdentityStatus.REVOKED:
                return RuleViolation(
                    rule_name="REVOKED_IDENTITY_IMMUTABLE",
                    category=RuleCategory.STATUS,
                    description=f"Cannot perform '{operation}' on a revoked Digital Identity",
                )
        except IdentityNotFoundError:
            pass  # Let other validation handle non-existent IDs
        return None
    
    def check_attribute_mutability(
        self,
        attribute_name: str,
    ) -> Optional[RuleViolation]:
        """Check if an attribute can be modified."""
        if attribute_name in AttributeKeeper.IMMUTABLE_ATTRIBUTES:
            return RuleViolation(
                rule_name="IMMUTABLE_ATTRIBUTE",
                category=RuleCategory.MUTABILITY,
                description=f"Attribute '{attribute_name}' is immutable and cannot be modified",
            )
        if attribute_name not in AttributeKeeper.MODIFIABLE_ATTRIBUTES:
            return RuleViolation(
                rule_name="UNKNOWN_ATTRIBUTE",
                category=RuleCategory.MUTABILITY,
                description=f"Attribute '{attribute_name}' is not a recognised modifiable attribute",
            )
        return None
    
    def check_access_tier_for_operation(
        self,
        actor_id: str,
        operation: str,
    ) -> Optional[RuleViolation]:
        """Check if organisation has required access tier for operation."""
        if not self._registry.can_perform_operation(actor_id, operation):
            return RuleViolation(
                rule_name="INSUFFICIENT_ACCESS_TIER",
                category=RuleCategory.ACCESS_LEVEL,
                description=f"Organisation does not have permission for operation '{operation}'",
            )
        return None
    
    def enforce_creation_rules(self, actor_id: str) -> None:
        """
        Enforce all rules for identity creation.
        
        Raises appropriate exception if any rule is violated.
        """
        violation = self.check_authority_for_creation(actor_id)
        if violation:
            raise AuthorisationDeniedError(violation.description)
    
    def enforce_update_rules(
        self,
        actor_id: str,
        identity_ref: str,
        attribute_name: str,
    ) -> None:
        """
        Enforce all rules for attribute updates.
        
        Checks rules in precedence order and raises exception
        for the first violation found.
        """
        # 1. Authority check
        violation = self.check_authority_for_update(actor_id)
        if violation:
            raise AuthorisationDeniedError(violation.description)
        
        # 2. Status check (revoked)
        violation = self.check_identity_not_revoked(identity_ref, "attribute_update")
        if violation:
            raise RevokedIdentityError(identity_ref, "attribute_update")
        
        # 3. Mutability check
        violation = self.check_attribute_mutability(attribute_name)
        if violation:
            raise ImmutableAttributeViolation(attribute_name)
    
    def enforce_status_change_rules(
        self,
        actor_id: str,
        identity_ref: str,
    ) -> None:
        """
        Enforce all rules for status changes.
        
        Note: Valid transition checking is handled by StatusSentinel.
        """
        # 1. Authority check
        violation = self.check_authority_for_creation(actor_id)
        if violation:
            raise AuthorisationDeniedError(violation.description)
        
        # 2. Status check (revoked)
        violation = self.check_identity_not_revoked(identity_ref, "status_change")
        if violation:
            raise RevokedIdentityError(identity_ref, "status_change")
    
    def enforce_verification_rules(
        self,
        actor_id: str,
        operation: str,
    ) -> None:
        """
        Enforce rules for verification operations.
        
        Verifies organisation is registered and has required access tier.
        """
        if not self._registry.is_registered(actor_id):
            raise AuthorisationDeniedError("Organisation is not registered")
        
        if not self._registry.is_active(actor_id):
            raise AuthorisationDeniedError("Organisation is not active")
        
        violation = self.check_access_tier_for_operation(actor_id, operation)
        if violation:
            raise InsufficientAccessTierError()
    
    def validate_all_rules(
        self,
        actor_id: str,
        operation: str,
        identity_ref: Optional[str] = None,
        attribute_name: Optional[str] = None,
    ) -> List[RuleViolation]:
        """
        Check all applicable rules and return list of violations.
        
        Does not raise exceptions - returns all violations found.
        Useful for comprehensive validation reporting.
        """
        violations = []
        
        # Authority checks based on operation
        if operation in ("create_identity", "update_attribute", "change_status"):
            violation = self.check_authority_for_creation(actor_id)
            if violation:
                violations.append(violation)
        
        # Status checks if identity specified
        if identity_ref and operation in ("update_attribute", "change_status"):
            violation = self.check_identity_not_revoked(identity_ref, operation)
            if violation:
                violations.append(violation)
        
        # Mutability checks if attribute specified
        if attribute_name and operation == "update_attribute":
            violation = self.check_attribute_mutability(attribute_name)
            if violation:
                violations.append(violation)
        
        # Access tier checks for verification operations
        if operation.startswith("verify"):
            violation = self.check_access_tier_for_operation(actor_id, operation)
            if violation:
                violations.append(violation)
        
        return violations
