"""
Tests for the CommandDeck console interface.

Tests the command-line interface functionality including command parsing,
identity management commands, verification commands, and system operations.
"""

import pytest
from datetime import date, datetime
from io import StringIO
from unittest.mock import patch, MagicMock

from nexus_digital_id.interface.command_deck import CommandDeck
from nexus_digital_id.core.identity_vault import IdentityStatus
from nexus_digital_id.authority.org_registry import OrganisationType, AccessTier
from nexus_digital_id.exceptions import (
    IdentityNotFoundError,
    AuthorisationDeniedError,
    ValidationFailureError,
)


class TestCommandDeckInitialisation:
    """Tests for CommandDeck initialisation."""

    def test_initialisation_creates_subsystems(self):
        """CommandDeck should initialise all required subsystems."""
        deck = CommandDeck()
        
        assert deck._vault is not None
        assert deck._registry is not None
        assert deck._central_command is not None
        assert deck._portal is not None
        assert deck._audit is not None
        assert deck._validator is not None

    def test_initialisation_sets_default_org_context(self):
        """CommandDeck should default to Central Authority context."""
        deck = CommandDeck()
        
        assert deck._current_org_id == "NEXUS-CENTRAL-001"
        assert "Central Authority" in deck._current_org_name

    def test_initialisation_registers_all_commands(self):
        """CommandDeck should register all expected commands."""
        deck = CommandDeck()
        
        expected_commands = [
            "create-id", "update-attr", "suspend", "reactivate", "revoke",
            "add-restriction", "remove-restriction", "view-id",
            "verify-basic", "verify-tax", "verify-driving",
            "register-org", "list-orgs", "switch-org",
            "stats", "audit-log", "demo", "help", "exit",
        ]
        
        for cmd in expected_commands:
            assert cmd in deck._commands


class TestArgumentParsing:
    """Tests for command argument parsing."""

    def test_parse_simple_args(self):
        """Should parse simple --key value pairs."""
        deck = CommandDeck()
        
        result = deck._parse_args("--id DID-12345 --name John")
        
        assert result["id"] == "DID-12345"
        assert result["name"] == "John"

    def test_parse_quoted_args(self):
        """Should parse quoted values with spaces."""
        deck = CommandDeck()
        
        result = deck._parse_args('--name "John Smith" --city London')
        
        assert result["name"] == "John Smith"
        assert result["city"] == "London"

    def test_parse_single_quoted_args(self):
        """Should parse single-quoted values."""
        deck = CommandDeck()
        
        result = deck._parse_args("--name 'Jane Doe' --id DID-999")
        
        assert result["name"] == "Jane Doe"
        assert result["id"] == "DID-999"

    def test_parse_empty_args(self):
        """Should return empty dict for empty args."""
        deck = CommandDeck()
        
        result = deck._parse_args("")
        
        assert result == {}


class TestProcessCommand:
    """Tests for command processing."""

    def test_process_unknown_command(self, capsys):
        """Should print error for unknown commands."""
        deck = CommandDeck()
        
        deck._process_command("unknown-cmd")
        
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_process_command_handles_nexus_exception(self, capsys):
        """Should handle NexusBaseException gracefully."""
        deck = CommandDeck()
        
        # Try to view non-existent identity
        deck._process_command("view-id --id DID-nonexistent")
        
        captured = capsys.readouterr()
        assert "Error" in captured.out


class TestIdentityCommands:
    """Tests for identity management commands."""

    def test_create_id_shows_usage_without_args(self, capsys):
        """create-id without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_create_identity("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "create-id" in captured.out

    def test_create_id_validates_required_fields(self, capsys):
        """create-id should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_create_identity("--name John")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out

    def test_create_id_validates_date_format(self, capsys):
        """create-id should validate date format."""
        deck = CommandDeck()
        
        args = ('--name "John Smith" --dob invalid-date --pob London '
                '--nat-birth GBR --address "123 Street" --email j@test.com '
                '--phone +447000000000 --nat-current GBR')
        deck._cmd_create_identity(args)
        
        captured = capsys.readouterr()
        assert "Invalid date format" in captured.out

    def test_create_id_success(self, capsys):
        """create-id should create identity with valid args."""
        deck = CommandDeck()
        
        args = ('--name "John Smith" --dob 1990-05-15 --pob London '
                '--nat-birth GBR --address "123 High Street" --email john@test.com '
                '--phone +447000000000 --nat-current GBR')
        deck._cmd_create_identity(args)
        
        captured = capsys.readouterr()
        assert "Identity created" in captured.out or "Existing identity" in captured.out

    def test_update_attr_shows_usage_without_args(self, capsys):
        """update-attr without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_update_attribute("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_update_attr_validates_required_fields(self, capsys):
        """update-attr should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_update_attribute("--id DID-123")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out

    def test_suspend_shows_usage_without_args(self, capsys):
        """suspend without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_suspend("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_suspend_validates_required_fields(self, capsys):
        """suspend should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_suspend("--reason test")
        
        captured = capsys.readouterr()
        assert "Missing required field" in captured.out

    def test_reactivate_shows_usage_without_args(self, capsys):
        """reactivate without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_reactivate("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_revoke_shows_usage_without_args(self, capsys):
        """revoke without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_revoke("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_view_id_shows_usage_without_args(self, capsys):
        """view-id without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_view_identity("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out


class TestRestrictionCommands:
    """Tests for restriction management commands."""

    def test_add_restriction_shows_usage_without_args(self, capsys):
        """add-restriction without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_add_restriction("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_add_restriction_validates_required_fields(self, capsys):
        """add-restriction should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_add_restriction("--id DID-123")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out

    def test_add_restriction_validates_date_format(self, capsys):
        """add-restriction should validate date format."""
        deck = CommandDeck()
        
        deck._cmd_add_restriction("--id DID-123 --type MEDICAL --effective bad-date")
        
        captured = capsys.readouterr()
        assert "Invalid date format" in captured.out

    def test_remove_restriction_shows_usage_without_args(self, capsys):
        """remove-restriction without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_remove_restriction("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_remove_restriction_validates_required_fields(self, capsys):
        """remove-restriction should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_remove_restriction("--id DID-123")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out


class TestVerificationCommands:
    """Tests for verification commands."""

    def test_verify_basic_shows_usage_without_args(self, capsys):
        """verify-basic without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_verify_basic("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_verify_basic_validates_required_fields(self, capsys):
        """verify-basic should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_verify_basic("--other value")
        
        captured = capsys.readouterr()
        assert "Missing required field" in captured.out

    def test_verify_tax_shows_usage_without_args(self, capsys):
        """verify-tax without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_verify_tax("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_verify_tax_validates_required_fields(self, capsys):
        """verify-tax should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_verify_tax("--id DID-123")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out

    def test_verify_tax_validates_date_format(self, capsys):
        """verify-tax should validate date format."""
        deck = CommandDeck()
        
        deck._cmd_verify_tax("--id DID-123 --start bad-date --end 2024-01-01")
        
        captured = capsys.readouterr()
        assert "Invalid date format" in captured.out

    def test_verify_driving_shows_usage_without_args(self, capsys):
        """verify-driving without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_verify_driving("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out


class TestOrganisationCommands:
    """Tests for organisation management commands."""

    def test_register_org_shows_usage_without_args(self, capsys):
        """register-org without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_register_org("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "Organisation Types:" in captured.out

    def test_register_org_validates_required_fields(self, capsys):
        """register-org should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_register_org("--name TestOrg")
        
        captured = capsys.readouterr()
        assert "Missing required fields" in captured.out

    def test_register_org_validates_org_type(self, capsys):
        """register-org should validate organisation type."""
        deck = CommandDeck()
        
        deck._cmd_register_org("--name TestOrg --type INVALID_TYPE")
        
        captured = capsys.readouterr()
        assert "Invalid organisation type" in captured.out

    def test_register_org_validates_access_tier(self, capsys):
        """register-org should validate access tier."""
        deck = CommandDeck()
        
        deck._cmd_register_org("--name TestOrg --type EMPLOYER --tier INVALID")
        
        captured = capsys.readouterr()
        assert "Invalid access tier" in captured.out

    def test_register_org_success(self, capsys):
        """register-org should register organisation with valid args."""
        deck = CommandDeck()
        
        deck._cmd_register_org("--name TestEmployer --type EMPLOYER --tier BASIC")
        
        captured = capsys.readouterr()
        assert "Organisation registered" in captured.out

    def test_list_orgs_displays_organisations(self, capsys):
        """list-orgs should display registered organisations."""
        deck = CommandDeck()
        
        deck._cmd_list_orgs("")
        
        captured = capsys.readouterr()
        assert "Registered Organisations" in captured.out
        assert "Central Authority" in captured.out

    def test_switch_org_shows_usage_without_args(self, capsys):
        """switch-org without args should show usage."""
        deck = CommandDeck()
        
        deck._cmd_switch_org("")
        
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_switch_org_validates_required_fields(self, capsys):
        """switch-org should validate required fields."""
        deck = CommandDeck()
        
        deck._cmd_switch_org("--other value")
        
        captured = capsys.readouterr()
        assert "Missing required field" in captured.out

    def test_switch_org_validates_org_exists(self, capsys):
        """switch-org should validate organisation exists."""
        deck = CommandDeck()
        
        deck._cmd_switch_org("--id NONEXISTENT-ORG")
        
        captured = capsys.readouterr()
        assert "Organisation not found" in captured.out

    def test_switch_org_success(self, capsys):
        """switch-org should switch to valid organisation."""
        deck = CommandDeck()
        
        # First register an org
        deck._cmd_register_org("--name TestBank --type BANK --tier BASIC")
        
        # Get the org ID from the output
        captured = capsys.readouterr()
        # Extract org ID from output
        import re
        match = re.search(r'ORG-[a-f0-9]+', captured.out)
        if match:
            org_id = match.group(0)
            deck._cmd_switch_org(f"--id {org_id}")
            
            captured = capsys.readouterr()
            assert "Switched to" in captured.out


class TestSystemCommands:
    """Tests for system commands."""

    def test_stats_displays_statistics(self, capsys):
        """stats should display system statistics."""
        deck = CommandDeck()
        
        deck._cmd_stats("")
        
        captured = capsys.readouterr()
        assert "System Statistics" in captured.out
        assert "Digital Identities" in captured.out
        assert "Organisations" in captured.out

    def test_audit_log_displays_entries(self, capsys):
        """audit-log should display audit entries."""
        deck = CommandDeck()
        
        deck._cmd_audit_log("")
        
        captured = capsys.readouterr()
        assert "Recent Audit Entries" in captured.out

    def test_audit_log_respects_count_parameter(self, capsys):
        """audit-log should respect count parameter."""
        deck = CommandDeck()
        
        deck._cmd_audit_log("--count 5")
        
        captured = capsys.readouterr()
        assert "Recent Audit Entries" in captured.out

    def test_help_displays_help_text(self, capsys):
        """help should display help text."""
        deck = CommandDeck()
        
        deck._cmd_help("")
        
        captured = capsys.readouterr()
        assert "Available Commands" in captured.out
        assert "IDENTITY MANAGEMENT" in captured.out
        assert "VERIFICATION" in captured.out

    def test_exit_raises_system_exit(self):
        """exit should raise SystemExit."""
        deck = CommandDeck()
        
        with pytest.raises(SystemExit):
            deck._cmd_exit("")


class TestDemoCommand:
    """Tests for the demo command."""

    def test_demo_runs_demonstration(self, capsys):
        """demo should run demonstration scenario."""
        deck = CommandDeck()
        
        deck._cmd_demo("")
        
        captured = capsys.readouterr()
        assert "Running Demonstration Scenario" in captured.out
        assert "Creating sample identities" in captured.out


class TestPrintHelpers:
    """Tests for print helper methods."""

    def test_print_success(self, capsys):
        """_print_success should print with checkmark."""
        deck = CommandDeck()
        
        deck._print_success("Test message")
        
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Test message" in captured.out

    def test_print_error(self, capsys):
        """_print_error should print with cross."""
        deck = CommandDeck()
        
        deck._print_error("Error message")
        
        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Error message" in captured.out

    def test_print_info(self, capsys):
        """_print_info should print with info symbol."""
        deck = CommandDeck()
        
        deck._print_info("Info message")
        
        captured = capsys.readouterr()
        assert "ℹ" in captured.out
        assert "Info message" in captured.out


class TestBannerAndHelp:
    """Tests for banner and help text."""

    def test_banner_exists(self):
        """CommandDeck should have a banner."""
        deck = CommandDeck()
        assert deck.BANNER is not None
        assert "Digital Identity Management System" in deck.BANNER

    def test_help_text_exists(self):
        """CommandDeck should have help text."""
        deck = CommandDeck()
        assert deck.HELP_TEXT is not None
        assert "Available Commands" in deck.HELP_TEXT


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""

    def test_full_identity_lifecycle(self, capsys):
        """Test complete identity lifecycle through commands."""
        deck = CommandDeck()
        
        # Create identity
        create_args = ('--name "Test Person" --dob 1985-06-20 --pob Bristol '
                      '--nat-birth GBR --address "1 Test Lane" --email test@test.com '
                      '--phone +447111111111 --nat-current GBR')
        deck._cmd_create_identity(create_args)
        
        captured = capsys.readouterr()
        assert "Identity created" in captured.out or "Existing identity" in captured.out
        
        # Extract identity ID
        import re
        match = re.search(r'DID-[a-f0-9]+', captured.out)
        if match:
            identity_id = match.group(0)
            
            # View identity
            deck._cmd_view_identity(f"--id {identity_id}")
            captured = capsys.readouterr()
            assert "Test Person" in captured.out
            
            # Suspend identity
            deck._cmd_suspend(f"--id {identity_id} --reason Testing")
            captured = capsys.readouterr()
            assert "suspended" in captured.out
            
            # Reactivate identity
            deck._cmd_reactivate(f"--id {identity_id}")
            captured = capsys.readouterr()
            assert "reactivated" in captured.out

    def test_verification_workflow(self, capsys):
        """Test verification workflow through commands."""
        deck = CommandDeck()
        
        # Create identity first
        create_args = ('--name "Verify Test" --dob 1990-01-01 --pob London '
                      '--nat-birth GBR --address "2 Verify St" --email verify@test.com '
                      '--phone +447222222222 --nat-current GBR')
        deck._cmd_create_identity(create_args)
        
        captured = capsys.readouterr()
        
        import re
        match = re.search(r'DID-[a-f0-9]+', captured.out)
        if match:
            identity_id = match.group(0)
            
            # Basic verification
            deck._cmd_verify_basic(f"--id {identity_id}")
            captured = capsys.readouterr()
            assert "Verification Result" in captured.out
            
            # Tax verification
            deck._cmd_verify_tax(f"--id {identity_id} --start 2023-04-06 --end 2024-04-05")
            captured = capsys.readouterr()
            assert "Tax Verification Result" in captured.out
            
            # Driving verification
            deck._cmd_verify_driving(f"--id {identity_id}")
            captured = capsys.readouterr()
            assert "Driving Eligibility Result" in captured.out
