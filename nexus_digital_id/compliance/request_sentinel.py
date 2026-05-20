"""
Nexus Digital ID - Request Sentinel

Validates all incoming requests for correct format and required fields
before they are processed by the system.

Validation Rules:
- All required fields must be present
- Field values must conform to expected formats
- Dates must be valid ISO 8601 format
- Email addresses must be valid format
- Phone numbers must contain valid characters
- Status values must be recognised
"""

import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from nexus_digital_id.exceptions import (
    MissingFieldError,
    InvalidFieldFormatError,
    ValidationFailureError,
)


@dataclass
class ValidationResult:
    """Result of request validation."""
    is_valid: bool
    missing_fields: List[str]
    invalid_fields: Dict[str, str]
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "missing_fields": self.missing_fields,
            "invalid_fields": self.invalid_fields,
        }


class RequestSentinel:
    """
    Request validation service for the Digital ID system.
    
    Validates incoming requests against defined schemas and
    format requirements before processing.
    
    Supported Request Types:
    - create_identity: New identity creation
    - update_attribute: Attribute modification
    - change_status: Status transition
    - verify_basic: Basic verification
    - verify_tax: Tax authority verification
    - verify_driving: Driving eligibility verification
    """
    
    # Field format patterns
    _PATTERNS = {
        "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        "phone": re.compile(r"^[\d\s\-\+]{7,20}$"),
        "identity_ref": re.compile(r"^DID-[a-f0-9]{8}$"),
        "org_id": re.compile(r"^[A-Z]{3,4}-[A-F0-9]{6}$|^NEXUS-CENTRAL-001$"),
        "nationality": re.compile(r"^[A-Z]{3}$"),  # ISO 3166-1 alpha-3
        "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),  # ISO 8601 date
    }
    
    # Required fields by request type
    _REQUIRED_FIELDS = {
        "create_identity": [
            "full_legal_name",
            "date_of_birth",
            "place_of_birth",
            "nationality_at_birth",
            "current_address",
            "contact_email",
            "contact_phone",
            "current_nationality",
        ],
        "update_attribute": [
            "identity_ref",
            "attribute_name",
            "new_value",
        ],
        "change_status": [
            "identity_ref",
            "new_status",
        ],
        "verify_basic": [
            "identity_ref",
            "requesting_org_id",
        ],
        "verify_tax": [
            "identity_ref",
            "requesting_org_id",
            "period_start",
            "period_end",
        ],
        "verify_driving": [
            "identity_ref",
            "requesting_org_id",
        ],
    }
    
    # Valid status values
    _VALID_STATUSES = frozenset(["ACTIVE", "SUSPENDED", "REVOKED"])
    
    # Modifiable attribute names
    _MODIFIABLE_ATTRIBUTES = frozenset([
        "current_address",
        "contact_email",
        "contact_phone",
        "current_nationality",
    ])
    
    def validate_request(
        self,
        request_type: str,
        request_data: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate a request against its schema.
        
        Args:
            request_type: Type of request being validated
            request_data: The request data to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        missing_fields = []
        invalid_fields = {}
        
        # Check required fields
        required = self._REQUIRED_FIELDS.get(request_type, [])
        for field in required:
            if field not in request_data or request_data[field] is None:
                missing_fields.append(field)
        
        # If missing required fields, return early
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                missing_fields=missing_fields,
                invalid_fields={},
            )
        
        # Validate field formats based on request type
        if request_type == "create_identity":
            invalid_fields.update(self._validate_creation_fields(request_data))
        elif request_type == "update_attribute":
            invalid_fields.update(self._validate_update_fields(request_data))
        elif request_type == "change_status":
            invalid_fields.update(self._validate_status_fields(request_data))
        elif request_type.startswith("verify"):
            invalid_fields.update(self._validate_verification_fields(request_data, request_type))
        
        return ValidationResult(
            is_valid=len(invalid_fields) == 0,
            missing_fields=[],
            invalid_fields=invalid_fields,
        )
    
    def _validate_creation_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate fields for identity creation."""
        errors = {}
        
        # Validate name
        name = data.get("full_legal_name", "")
        if not name or len(name.strip()) == 0:
            errors["full_legal_name"] = "Name cannot be empty"
        elif len(name) > 200:
            errors["full_legal_name"] = "Name exceeds maximum length of 200 characters"
        elif not re.match(r"^[a-zA-Z\s\-\']+$", name):
            errors["full_legal_name"] = "Name contains invalid characters"
        
        # Validate date of birth
        dob = data.get("date_of_birth")
        dob_error = self._validate_date(dob, "date_of_birth", allow_future=False)
        if dob_error:
            errors["date_of_birth"] = dob_error
        
        # Validate place of birth
        pob = data.get("place_of_birth", "")
        if not pob or len(pob.strip()) == 0:
            errors["place_of_birth"] = "Place of birth cannot be empty"
        elif len(pob) > 200:
            errors["place_of_birth"] = "Place of birth exceeds maximum length"
        
        # Validate nationalities
        for field in ["nationality_at_birth", "current_nationality"]:
            nat = data.get(field, "")
            if not self._PATTERNS["nationality"].match(str(nat)):
                errors[field] = "Must be a valid ISO 3166-1 alpha-3 country code"
        
        # Validate address
        address = data.get("current_address", "")
        if not address or len(address.strip()) == 0:
            errors["current_address"] = "Address cannot be empty"
        elif len(address) > 500:
            errors["current_address"] = "Address exceeds maximum length of 500 characters"
        
        # Validate email
        email = data.get("contact_email", "")
        if not self._PATTERNS["email"].match(str(email)):
            errors["contact_email"] = "Invalid email format"
        elif len(email) > 254:
            errors["contact_email"] = "Email exceeds maximum length"
        
        # Validate phone
        phone = data.get("contact_phone", "")
        if not self._PATTERNS["phone"].match(str(phone)):
            errors["contact_phone"] = "Invalid phone format (7-20 characters, digits/spaces/hyphens/plus)"
        
        return errors
    
    def _validate_update_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate fields for attribute update."""
        errors = {}
        
        # Validate identity reference
        identity_ref = data.get("identity_ref", "")
        if not self._PATTERNS["identity_ref"].match(str(identity_ref)):
            errors["identity_ref"] = "Invalid identity reference format (expected DID-xxxxxxxx)"
        
        # Validate attribute name
        attr_name = data.get("attribute_name", "")
        if attr_name not in self._MODIFIABLE_ATTRIBUTES:
            errors["attribute_name"] = f"'{attr_name}' is not a modifiable attribute"
        
        # Validate new value based on attribute type
        new_value = data.get("new_value", "")
        if attr_name == "contact_email":
            if not self._PATTERNS["email"].match(str(new_value)):
                errors["new_value"] = "Invalid email format"
        elif attr_name == "contact_phone":
            if not self._PATTERNS["phone"].match(str(new_value)):
                errors["new_value"] = "Invalid phone format"
        elif attr_name == "current_nationality":
            if not self._PATTERNS["nationality"].match(str(new_value)):
                errors["new_value"] = "Must be a valid ISO 3166-1 alpha-3 country code"
        elif attr_name == "current_address":
            if not new_value or len(str(new_value).strip()) == 0:
                errors["new_value"] = "Address cannot be empty"
            elif len(str(new_value)) > 500:
                errors["new_value"] = "Address exceeds maximum length"
        
        return errors
    
    def _validate_status_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate fields for status change."""
        errors = {}
        
        # Validate identity reference
        identity_ref = data.get("identity_ref", "")
        if not self._PATTERNS["identity_ref"].match(str(identity_ref)):
            errors["identity_ref"] = "Invalid identity reference format"
        
        # Validate status value
        new_status = data.get("new_status", "")
        if str(new_status).upper() not in self._VALID_STATUSES:
            errors["new_status"] = f"Invalid status. Must be one of: {', '.join(self._VALID_STATUSES)}"
        
        return errors
    
    def _validate_verification_fields(
        self,
        data: Dict[str, Any],
        request_type: str,
    ) -> Dict[str, str]:
        """Validate fields for verification requests."""
        errors = {}
        
        # Validate identity reference
        identity_ref = data.get("identity_ref", "")
        if not self._PATTERNS["identity_ref"].match(str(identity_ref)):
            errors["identity_ref"] = "Invalid identity reference format"
        
        # Validate organisation ID
        org_id = data.get("requesting_org_id", "")
        if not self._PATTERNS["org_id"].match(str(org_id)):
            errors["requesting_org_id"] = "Invalid organisation ID format"
        
        # Additional validation for tax verification
        if request_type == "verify_tax":
            start_error = self._validate_date(
                data.get("period_start"), "period_start", allow_future=True
            )
            if start_error:
                errors["period_start"] = start_error
            
            end_error = self._validate_date(
                data.get("period_end"), "period_end", allow_future=True
            )
            if end_error:
                errors["period_end"] = end_error
            
            # Check period_end >= period_start
            if not start_error and not end_error:
                start = self._parse_date(data.get("period_start"))
                end = self._parse_date(data.get("period_end"))
                if start and end and end < start:
                    errors["period_end"] = "End date cannot precede start date"
        
        return errors
    
    def _validate_date(
        self,
        value: Any,
        field_name: str,
        allow_future: bool = True,
    ) -> Optional[str]:
        """Validate a date value."""
        if value is None:
            return f"{field_name} is required"
        
        # If already a date object
        if isinstance(value, date):
            if not allow_future and value > date.today():
                return f"{field_name} cannot be in the future"
            return None
        
        # If string, validate format
        if isinstance(value, str):
            if not self._PATTERNS["date"].match(value):
                return "Invalid date format (expected YYYY-MM-DD)"
            
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d").date()
                if not allow_future and parsed > date.today():
                    return f"{field_name} cannot be in the future"
            except ValueError:
                return "Invalid date value"
        
        return None
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value to date object."""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None
    
    def validate_and_raise(
        self,
        request_type: str,
        request_data: Dict[str, Any],
    ) -> None:
        """
        Validate request and raise exception if invalid.
        
        Raises:
            MissingFieldError: If required fields are missing
            InvalidFieldFormatError: If field values are invalid
        """
        result = self.validate_request(request_type, request_data)
        
        if result.missing_fields:
            raise MissingFieldError(result.missing_fields)
        
        if result.invalid_fields:
            raise InvalidFieldFormatError(result.invalid_fields)
