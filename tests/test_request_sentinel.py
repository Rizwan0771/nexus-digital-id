"""
Nexus Digital ID - Request Sentinel Tests

Tests for request validation.
"""

import pytest
from datetime import date

from nexus_digital_id.compliance.request_sentinel import RequestSentinel
from nexus_digital_id.exceptions import MissingFieldError, InvalidFieldFormatError


class TestCreationValidation:
    """Tests for identity creation request validation."""
    
    def test_valid_creation_request(self, request_sentinel):
        """Should pass validation for valid creation request."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is True
        assert len(result.missing_fields) == 0
        assert len(result.invalid_fields) == 0
    
    def test_missing_required_fields(self, request_sentinel):
        """Should detect missing required fields."""
        data = {
            "full_legal_name": "Test Person",
            # Missing other required fields
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert len(result.missing_fields) > 0
    
    def test_invalid_email_format(self, request_sentinel):
        """Should detect invalid email format."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "not-an-email",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert "contact_email" in result.invalid_fields
    
    def test_invalid_phone_format(self, request_sentinel):
        """Should detect invalid phone format."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "abc",  # Invalid
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert "contact_phone" in result.invalid_fields
    
    def test_invalid_nationality_format(self, request_sentinel):
        """Should detect invalid nationality code."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "INVALID",  # Should be 3 chars
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert "nationality_at_birth" in result.invalid_fields
    
    def test_name_with_invalid_characters(self, request_sentinel):
        """Should detect invalid characters in name."""
        data = {
            "full_legal_name": "Test123 Person!",  # Invalid chars
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert "full_legal_name" in result.invalid_fields
    
    def test_future_date_of_birth(self, request_sentinel):
        """Should reject future date of birth."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "2099-05-15",  # Future date
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        result = request_sentinel.validate_request("create_identity", data)
        
        assert result.is_valid is False
        assert "date_of_birth" in result.invalid_fields


class TestUpdateValidation:
    """Tests for attribute update request validation."""
    
    def test_valid_update_request(self, request_sentinel):
        """Should pass validation for valid update request."""
        data = {
            "identity_ref": "DID-12345678",
            "attribute_name": "current_address",
            "new_value": "New Address",
        }
        
        result = request_sentinel.validate_request("update_attribute", data)
        
        assert result.is_valid is True
    
    def test_invalid_identity_ref_format(self, request_sentinel):
        """Should detect invalid identity reference format."""
        data = {
            "identity_ref": "INVALID-FORMAT",
            "attribute_name": "current_address",
            "new_value": "New Address",
        }
        
        result = request_sentinel.validate_request("update_attribute", data)
        
        assert result.is_valid is False
        assert "identity_ref" in result.invalid_fields
    
    def test_invalid_attribute_name(self, request_sentinel):
        """Should detect invalid attribute name."""
        data = {
            "identity_ref": "DID-12345678",
            "attribute_name": "invalid_attribute",
            "new_value": "Value",
        }
        
        result = request_sentinel.validate_request("update_attribute", data)
        
        assert result.is_valid is False
        assert "attribute_name" in result.invalid_fields


class TestStatusChangeValidation:
    """Tests for status change request validation."""
    
    def test_valid_status_change(self, request_sentinel):
        """Should pass validation for valid status change."""
        data = {
            "identity_ref": "DID-12345678",
            "new_status": "SUSPENDED",
        }
        
        result = request_sentinel.validate_request("change_status", data)
        
        assert result.is_valid is True
    
    def test_invalid_status_value(self, request_sentinel):
        """Should detect invalid status value."""
        data = {
            "identity_ref": "DID-12345678",
            "new_status": "INVALID_STATUS",
        }
        
        result = request_sentinel.validate_request("change_status", data)
        
        assert result.is_valid is False
        assert "new_status" in result.invalid_fields


class TestVerificationValidation:
    """Tests for verification request validation."""
    
    def test_valid_basic_verification(self, request_sentinel):
        """Should pass validation for valid basic verification."""
        data = {
            "identity_ref": "DID-12345678",
            "requesting_org_id": "BANK-ABC123",
        }
        
        result = request_sentinel.validate_request("verify_basic", data)
        
        assert result.is_valid is True
    
    def test_valid_tax_verification(self, request_sentinel):
        """Should pass validation for valid tax verification."""
        data = {
            "identity_ref": "DID-12345678",
            "requesting_org_id": "TAX-ABC123",
            "period_start": "2024-04-06",
            "period_end": "2025-04-05",
        }
        
        result = request_sentinel.validate_request("verify_tax", data)
        
        assert result.is_valid is True
    
    def test_tax_verification_end_before_start(self, request_sentinel):
        """Should detect when end date precedes start date."""
        data = {
            "identity_ref": "DID-12345678",
            "requesting_org_id": "TAX-ABC123",
            "period_start": "2025-04-05",
            "period_end": "2024-04-06",  # Before start
        }
        
        result = request_sentinel.validate_request("verify_tax", data)
        
        assert result.is_valid is False
        assert "period_end" in result.invalid_fields


class TestValidateAndRaise:
    """Tests for validate_and_raise method."""
    
    def test_raises_missing_field_error(self, request_sentinel):
        """Should raise MissingFieldError for missing fields."""
        data = {"full_legal_name": "Test"}  # Missing other fields
        
        with pytest.raises(MissingFieldError) as exc_info:
            request_sentinel.validate_and_raise("create_identity", data)
        
        assert len(exc_info.value.missing_fields) > 0
    
    def test_raises_invalid_field_error(self, request_sentinel):
        """Should raise InvalidFieldFormatError for invalid fields."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "invalid-email",  # Invalid
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        with pytest.raises(InvalidFieldFormatError) as exc_info:
            request_sentinel.validate_and_raise("create_identity", data)
        
        assert "contact_email" in exc_info.value.field_errors
    
    def test_no_exception_for_valid_request(self, request_sentinel):
        """Should not raise exception for valid request."""
        data = {
            "full_legal_name": "Test Person",
            "date_of_birth": "1990-05-15",
            "place_of_birth": "London",
            "nationality_at_birth": "GBR",
            "current_address": "123 Test Street",
            "contact_email": "test@example.com",
            "contact_phone": "+447000000000",
            "current_nationality": "GBR",
        }
        
        # Should not raise
        request_sentinel.validate_and_raise("create_identity", data)
