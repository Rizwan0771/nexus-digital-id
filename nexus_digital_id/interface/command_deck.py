"""
Nexus Digital ID - Command Deck

Console-based interface for interacting with the Digital ID system.
Provides commands for identity management, verification, and administration.
"""

import json
import sys
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from nexus_digital_id.core.identity_vault import (
    DigitalIdentityVault,
    IdentityStatus,
    ImmutableAttributes,
    ModifiableAttributes,
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
from nexus_digital_id.compliance.audit_chronicle import AuditChronicle, AuditEventType
from nexus_digital_id.compliance.request_sentinel import RequestSentinel
from nexus_digital_id.exceptions import NexusBaseException


class CommandDeck:
    """
    Interactive console interface for the Nexus Digital ID system.
    
    Provides a command-line interface for:
    - Creating and managing Digital Identities
    - Updating identity attributes
    - Managing identity status
    - Performing verifications as different organisations
    - Viewing audit logs and system statistics
    """
    
    BANNER = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗              ║
    ║     ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝              ║
    ║     ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗              ║
    ║     ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║              ║
    ║     ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║              ║
    ║     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝              ║
    ║                                                               ║
    ║           Digital Identity Management System                  ║
    ║                     Version 1.0.0                             ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    
    HELP_TEXT = """
Available Commands:
═══════════════════════════════════════════════════════════════════

IDENTITY MANAGEMENT (Central Authority Only):
  create-id          Create a new Digital Identity
  update-attr        Update a modifiable attribute
  suspend            Suspend an active identity
  reactivate         Reactivate a suspended identity  
  revoke             Permanently revoke an identity
  add-restriction    Add a temporary restriction
  remove-restriction Remove a temporary restriction
  view-id            View identity details

VERIFICATION (Consuming Organisations):
  verify-basic       Basic validity check
  verify-tax         Tax authority period verification
  verify-driving     Driving licence eligibility check

ORGANISATION MANAGEMENT:
  register-org       Register a new organisation
  list-orgs          List registered organisations
  switch-org         Switch active organisation context

SYSTEM:
  stats              View system statistics
  audit-log          View recent audit entries
  demo               Run demonstration scenario
  help               Show this help message
  exit               Exit the system

Type 'help <command>' for detailed usage of a specific command.
"""

    def __init__(self):
        """Initialise the Command Deck with all subsystems."""
        self._vault = DigitalIdentityVault()
        self._registry = OrganisationRegistry()
        self._central_command = CentralCommand(self._vault, self._registry)
        self._portal = PortalGateway(self._vault, self._registry)
        self._audit = AuditChronicle()
        self._validator = RequestSentinel()
        
        # Current organisation context (defaults to Central Authority)
        self._current_org_id = OrganisationRegistry.CENTRAL_AUTHORITY_ID
        self._current_org_name = OrganisationRegistry.CENTRAL_AUTHORITY_NAME
        
        # Command handlers
        self._commands = {
            "create-id": self._cmd_create_identity,
            "update-attr": self._cmd_update_attribute,
            "suspend": self._cmd_suspend,
            "reactivate": self._cmd_reactivate,
            "revoke": self._cmd_revoke,
            "add-restriction": self._cmd_add_restriction,
            "remove-restriction": self._cmd_remove_restriction,
            "view-id": self._cmd_view_identity,
            "verify-basic": self._cmd_verify_basic,
            "verify-tax": self._cmd_verify_tax,
            "verify-driving": self._cmd_verify_driving,
            "register-org": self._cmd_register_org,
            "list-orgs": self._cmd_list_orgs,
            "switch-org": self._cmd_switch_org,
            "stats": self._cmd_stats,
            "audit-log": self._cmd_audit_log,
            "demo": self._cmd_demo,
            "help": self._cmd_help,
            "exit": self._cmd_exit,
        }
    
    def run(self) -> None:
        """Start the interactive console session."""
        print(self.BANNER)
        print("Type 'help' for available commands.\n")
        
        while True:
            try:
                prompt = f"nexus [{self._current_org_name}]> "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                self._process_command(user_input)
                
            except KeyboardInterrupt:
                print("\n\nUse 'exit' to quit properly.")
            except EOFError:
                print("\nExiting...")
                break
    
    def _process_command(self, user_input: str) -> None:
        """Parse and execute a command."""
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command in self._commands:
            try:
                self._commands[command](args)
            except NexusBaseException as e:
                self._print_error(e.message)
            except Exception as e:
                self._print_error(f"Unexpected error: {str(e)}")
        else:
            self._print_error(f"Unknown command: {command}")
            print("Type 'help' for available commands.")
    
    def _print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✓ {message}")
    
    def _print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"✗ Error: {message}")
    
    def _print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"ℹ {message}")

    def _parse_args(self, args: str) -> Dict[str, str]:
        """Parse command arguments in --key value format."""
        result = {}
        parts = args.split()
        i = 0
        while i < len(parts):
            if parts[i].startswith("--"):
                key = parts[i][2:]
                # Handle quoted values
                if i + 1 < len(parts):
                    value = parts[i + 1]
                    # Check for quoted string
                    if value.startswith('"') or value.startswith("'"):
                        quote_char = value[0]
                        value_parts = [value[1:]]
                        i += 2
                        while i < len(parts) and not parts[i-1].endswith(quote_char):
                            value_parts.append(parts[i])
                            i += 1
                        value = " ".join(value_parts)
                        if value.endswith(quote_char):
                            value = value[:-1]
                        result[key] = value
                        continue
                    result[key] = value
                    i += 2
                else:
                    result[key] = ""
                    i += 1
            else:
                i += 1
        return result

    def _cmd_create_identity(self, args: str) -> None:
        """Create a new Digital Identity."""
        if not args:
            print("Usage: create-id --name <name> --dob <YYYY-MM-DD> --pob <place>")
            print("       --nat-birth <XXX> --address <address> --email <email>")
            print("       --phone <phone> --nat-current <XXX>")
            print("\nExample:")
            print('  create-id --name "Eleanor Vance" --dob 1985-03-22 --pob Manchester')
            print('            --nat-birth GBR --address "42 Willow Lane" --email e.vance@mail.com')
            print('            --phone +447700900123 --nat-current GBR')
            return
        
        parsed = self._parse_args(args)
        
        required = ["name", "dob", "pob", "nat-birth", "address", "email", "phone", "nat-current"]
        missing = [f for f in required if f not in parsed]
        if missing:
            self._print_error(f"Missing required fields: {', '.join(missing)}")
            return
        
        try:
            dob = datetime.strptime(parsed["dob"], "%Y-%m-%d").date()
        except ValueError:
            self._print_error("Invalid date format. Use YYYY-MM-DD")
            return
        
        record, was_created = self._central_command.create_identity(
            requesting_org_id=self._current_org_id,
            full_legal_name=parsed["name"],
            date_of_birth=dob,
            place_of_birth=parsed["pob"],
            nationality_at_birth=parsed["nat-birth"].upper(),
            current_address=parsed["address"],
            contact_email=parsed["email"],
            contact_phone=parsed["phone"],
            current_nationality=parsed["nat-current"].upper(),
        )
        
        # Log the creation
        self._audit.record_identity_creation(
            actor_id=self._current_org_id,
            identity_ref=record.identity_ref,
            was_new=was_created,
        )
        
        if was_created:
            self._print_success(f"Identity created: {record.identity_ref}")
        else:
            self._print_info(f"Existing identity returned: {record.identity_ref}")
        
        print(f"  Name: {record.immutable_attrs.full_legal_name}")
        print(f"  Status: {record.current_status.value}")

    def _cmd_update_attribute(self, args: str) -> None:
        """Update a modifiable attribute."""
        if not args:
            print("Usage: update-attr --id <DID-xxxxxxxx> --attr <attribute> --value <new_value>")
            print("\nModifiable attributes:")
            print("  current_address, contact_email, contact_phone, current_nationality")
            return
        
        parsed = self._parse_args(args)
        
        if "id" not in parsed or "attr" not in parsed or "value" not in parsed:
            self._print_error("Missing required fields: --id, --attr, --value")
            return
        
        old_val, new_val, changed = self._central_command.update_attribute(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            attribute_name=parsed["attr"],
            new_value=parsed["value"],
        )
        
        self._audit.record_attribute_update(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            attribute_name=parsed["attr"],
            previous_value=old_val,
            new_value=new_val,
            was_changed=changed,
        )
        
        if changed:
            self._print_success(f"Attribute '{parsed['attr']}' updated")
            print(f"  Previous: {old_val}")
            print(f"  New: {new_val}")
        else:
            self._print_info("No change - value already set")

    def _cmd_suspend(self, args: str) -> None:
        """Suspend an active identity."""
        if not args:
            print("Usage: suspend --id <DID-xxxxxxxx> [--reason <reason>]")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        prev, new, _ = self._central_command.suspend_identity(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            reason=parsed.get("reason"),
        )
        
        self._audit.record_status_change(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            previous_status=prev.value,
            new_status=new.value,
            reason=parsed.get("reason"),
        )
        
        self._print_success(f"Identity {parsed['id']} suspended")

    def _cmd_reactivate(self, args: str) -> None:
        """Reactivate a suspended identity."""
        if not args:
            print("Usage: reactivate --id <DID-xxxxxxxx> [--reason <reason>]")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        prev, new, _ = self._central_command.reactivate_identity(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            reason=parsed.get("reason"),
        )
        
        self._audit.record_status_change(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            previous_status=prev.value,
            new_status=new.value,
            reason=parsed.get("reason"),
        )
        
        self._print_success(f"Identity {parsed['id']} reactivated")

    def _cmd_revoke(self, args: str) -> None:
        """Permanently revoke an identity."""
        if not args:
            print("Usage: revoke --id <DID-xxxxxxxx> [--reason <reason>]")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        prev, new, _ = self._central_command.revoke_identity(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            reason=parsed.get("reason"),
        )
        
        self._audit.record_status_change(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            previous_status=prev.value,
            new_status=new.value,
            reason=parsed.get("reason"),
        )
        
        self._print_success(f"Identity {parsed['id']} permanently revoked")

    def _cmd_add_restriction(self, args: str) -> None:
        """Add a temporary restriction to an identity."""
        if not args:
            print("Usage: add-restriction --id <DID-xxx> --type <type> --effective <YYYY-MM-DD>")
            print("       [--expiry <YYYY-MM-DD>] [--desc <description>]")
            return
        
        parsed = self._parse_args(args)
        required = ["id", "type", "effective"]
        missing = [f for f in required if f not in parsed]
        if missing:
            self._print_error(f"Missing required fields: {', '.join(missing)}")
            return
        
        try:
            effective = datetime.strptime(parsed["effective"], "%Y-%m-%d").date()
            expiry = None
            if "expiry" in parsed:
                expiry = datetime.strptime(parsed["expiry"], "%Y-%m-%d").date()
        except ValueError:
            self._print_error("Invalid date format. Use YYYY-MM-DD")
            return
        
        self._central_command.add_restriction(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            restriction_type=parsed["type"],
            effective_date=effective,
            expiry_date=expiry,
            description=parsed.get("desc"),
        )
        
        self._print_success(f"Restriction '{parsed['type']}' added to {parsed['id']}")

    def _cmd_remove_restriction(self, args: str) -> None:
        """Remove a temporary restriction from an identity."""
        if not args:
            print("Usage: remove-restriction --id <DID-xxxxxxxx> --type <restriction_type>")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed or "type" not in parsed:
            self._print_error("Missing required fields: --id, --type")
            return
        
        removed = self._central_command.remove_restriction(
            requesting_org_id=self._current_org_id,
            identity_ref=parsed["id"],
            restriction_type=parsed["type"],
        )
        
        if removed:
            self._print_success(f"Restriction '{parsed['type']}' removed")
        else:
            self._print_info("No matching restriction found")

    def _cmd_view_identity(self, args: str) -> None:
        """View details of a Digital Identity."""
        if not args:
            print("Usage: view-id --id <DID-xxxxxxxx> [--history]")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        record = self._central_command.get_identity(parsed["id"])
        include_history = "history" in parsed
        
        print(f"\n{'═' * 50}")
        print(f"Digital Identity: {record.identity_ref}")
        print(f"{'═' * 50}")
        print(f"Status: {record.current_status.value}")
        print(f"Created: {record.creation_timestamp.isoformat()}")
        print(f"\nImmutable Attributes:")
        print(f"  Name: {record.immutable_attrs.full_legal_name}")
        print(f"  Date of Birth: {record.immutable_attrs.date_of_birth}")
        print(f"  Place of Birth: {record.immutable_attrs.place_of_birth}")
        print(f"  Nationality at Birth: {record.immutable_attrs.nationality_at_birth}")
        print(f"\nModifiable Attributes:")
        print(f"  Address: {record.modifiable_attrs.current_address}")
        print(f"  Email: {record.modifiable_attrs.contact_email}")
        print(f"  Phone: {record.modifiable_attrs.contact_phone}")
        print(f"  Current Nationality: {record.modifiable_attrs.current_nationality}")
        
        if record.temporary_restrictions:
            print(f"\nTemporary Restrictions ({len(record.temporary_restrictions)}):")
            for r in record.temporary_restrictions:
                status = "ACTIVE" if r.is_active() else "INACTIVE"
                print(f"  - {r.restriction_type} [{status}]")
                print(f"    Effective: {r.effective_date}")
                if r.expiry_date:
                    print(f"    Expires: {r.expiry_date}")
        
        if include_history and record.status_history:
            print(f"\nStatus History:")
            for entry in record.status_history:
                prev = entry.previous_status.value if entry.previous_status else "N/A"
                print(f"  {entry.transition_timestamp.isoformat()}: {prev} -> {entry.new_status.value}")
                if entry.reason:
                    print(f"    Reason: {entry.reason}")
        
        print(f"{'═' * 50}\n")

    def _cmd_verify_basic(self, args: str) -> None:
        """Perform basic identity verification."""
        if not args:
            print("Usage: verify-basic --id <DID-xxxxxxxx>")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        result = self._portal.verify_basic(parsed["id"], self._current_org_id)
        
        self._audit.record_verification(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            verification_type="basic",
            result=result.outcome.value,
        )
        
        print(f"\nVerification Result:")
        print(f"  Identity: {result.identity_ref}")
        print(f"  Outcome: {result.outcome.value}")
        print(f"  Valid: {'Yes' if result.is_currently_valid else 'No'}")
        print(f"  Message: {result.message}")
        print(f"  Timestamp: {result.verification_timestamp.isoformat()}\n")

    def _cmd_verify_tax(self, args: str) -> None:
        """Perform tax authority verification for a reporting period."""
        if not args:
            print("Usage: verify-tax --id <DID-xxx> --start <YYYY-MM-DD> --end <YYYY-MM-DD>")
            return
        
        parsed = self._parse_args(args)
        required = ["id", "start", "end"]
        missing = [f for f in required if f not in parsed]
        if missing:
            self._print_error(f"Missing required fields: {', '.join(missing)}")
            return
        
        try:
            start = datetime.strptime(parsed["start"], "%Y-%m-%d").date()
            end = datetime.strptime(parsed["end"], "%Y-%m-%d").date()
        except ValueError:
            self._print_error("Invalid date format. Use YYYY-MM-DD")
            return
        
        result = self._portal.verify_for_tax_period(
            parsed["id"], start, end, self._current_org_id
        )
        
        self._audit.record_verification(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            verification_type="tax_period",
            result=result.outcome.value,
            additional_details={
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
            },
        )
        
        print(f"\nTax Verification Result:")
        print(f"  Identity: {result.identity_ref}")
        print(f"  Outcome: {result.outcome.value}")
        print(f"  Currently Active: {'Yes' if result.is_currently_active else 'No'}")
        print(f"  Continuously Active: {'Yes' if result.was_continuously_active else 'No'}")
        print(f"  Period: {start} to {end}")
        if result.suspension_periods:
            print(f"  Suspension Periods:")
            for sp in result.suspension_periods:
                print(f"    - {sp['suspension_start']} to {sp['suspension_end']}")
        print(f"  Message: {result.message}\n")

    def _cmd_verify_driving(self, args: str) -> None:
        """Perform driving licence eligibility verification."""
        if not args:
            print("Usage: verify-driving --id <DID-xxxxxxxx>")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        result = self._portal.verify_driving_eligibility(parsed["id"], self._current_org_id)
        
        self._audit.record_verification(
            actor_id=self._current_org_id,
            identity_ref=parsed["id"],
            verification_type="driving_eligibility",
            result=result.outcome.value,
        )
        
        print(f"\nDriving Eligibility Result:")
        print(f"  Identity: {result.identity_ref}")
        print(f"  Outcome: {result.outcome.value}")
        print(f"  Eligible: {'Yes' if result.is_eligible else 'No'}")
        print(f"  Has Restrictions: {'Yes' if result.has_restrictions else 'No'}")
        if result.has_restrictions:
            print(f"  Restriction Count: {result.restriction_count}")
        print(f"  Message: {result.message}\n")

    def _cmd_register_org(self, args: str) -> None:
        """Register a new consuming organisation."""
        if not args:
            print("Usage: register-org --name <name> --type <type> [--tier <tier>]")
            print("\nOrganisation Types:")
            print("  TAX_AUTHORITY, DRIVING_LICENCE_AUTHORITY, WELFARE_SERVICES,")
            print("  IMMIGRATION, LOCAL_AUTHORITY, EMPLOYER, BANK, OTHER")
            print("\nAccess Tiers: BASIC, STANDARD, ENHANCED")
            return
        
        parsed = self._parse_args(args)
        if "name" not in parsed or "type" not in parsed:
            self._print_error("Missing required fields: --name, --type")
            return
        
        try:
            org_type = OrganisationType[parsed["type"].upper()]
        except KeyError:
            self._print_error(f"Invalid organisation type: {parsed['type']}")
            return
        
        tier = None
        if "tier" in parsed:
            try:
                tier = AccessTier[parsed["tier"].upper()]
            except KeyError:
                self._print_error(f"Invalid access tier: {parsed['tier']}")
                return
        
        org = self._central_command.register_organisation(
            requesting_org_id=self._current_org_id,
            org_name=parsed["name"],
            org_type=org_type,
            access_tier=tier,
        )
        
        self._print_success(f"Organisation registered: {org.org_id}")
        print(f"  Name: {org.org_name}")
        print(f"  Type: {org.org_type.value}")
        print(f"  Access Tier: {org.access_tier.value}")

    def _cmd_list_orgs(self, args: str) -> None:
        """List all registered organisations."""
        orgs = self._registry.get_all_organisations(include_inactive=True)
        
        print(f"\nRegistered Organisations ({len(orgs)}):")
        print(f"{'─' * 70}")
        print(f"{'ID':<20} {'Name':<25} {'Type':<15} {'Tier':<10}")
        print(f"{'─' * 70}")
        
        for org in orgs:
            status = "" if org.is_active else " [INACTIVE]"
            print(f"{org.org_id:<20} {org.org_name[:24]:<25} {org.org_type.value[:14]:<15} {org.access_tier.value:<10}{status}")
        
        print(f"{'─' * 70}\n")

    def _cmd_switch_org(self, args: str) -> None:
        """Switch the active organisation context."""
        if not args:
            print("Usage: switch-org --id <ORG-ID>")
            print("\nUse 'list-orgs' to see available organisations.")
            print("Use 'NEXUS-CENTRAL-001' for Central Authority.")
            return
        
        parsed = self._parse_args(args)
        if "id" not in parsed:
            self._print_error("Missing required field: --id")
            return
        
        org = self._registry.get_organisation(parsed["id"])
        if not org:
            self._print_error(f"Organisation not found: {parsed['id']}")
            return
        
        if not org.is_active:
            self._print_error("Cannot switch to inactive organisation")
            return
        
        self._current_org_id = org.org_id
        self._current_org_name = org.org_name
        self._print_success(f"Switched to: {org.org_name}")
        print(f"  Access Tier: {org.access_tier.value}")

    def _cmd_stats(self, args: str) -> None:
        """Display system statistics."""
        stats = self._central_command.get_system_statistics()
        
        print(f"\n{'═' * 40}")
        print("System Statistics")
        print(f"{'═' * 40}")
        print(f"\nDigital Identities: {stats['total_identities']}")
        print(f"  Active: {stats['identities_by_status']['ACTIVE']}")
        print(f"  Suspended: {stats['identities_by_status']['SUSPENDED']}")
        print(f"  Revoked: {stats['identities_by_status']['REVOKED']}")
        print(f"\nOrganisations: {stats['total_organisations']}")
        print(f"  Basic Tier: {stats['organisations_by_tier']['BASIC']}")
        print(f"  Standard Tier: {stats['organisations_by_tier']['STANDARD']}")
        print(f"  Enhanced Tier: {stats['organisations_by_tier']['ENHANCED']}")
        print(f"\nAudit Entries: {self._audit.count_entries()}")
        print(f"{'═' * 40}\n")

    def _cmd_audit_log(self, args: str) -> None:
        """View recent audit log entries."""
        parsed = self._parse_args(args) if args else {}
        count = int(parsed.get("count", "10"))
        
        entries = self._audit.get_recent_entries(count)
        
        print(f"\nRecent Audit Entries (last {len(entries)}):")
        print(f"{'─' * 80}")
        
        for entry in entries:
            id_ref = entry.identity_ref or "N/A"
            print(f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {entry.event_type.value}")
            print(f"  Actor: {entry.actor_id} | Identity: {id_ref} | {entry.outcome}")
        
        print(f"{'─' * 80}\n")

    def _cmd_demo(self, args: str) -> None:
        """Run a demonstration scenario."""
        print("\n" + "=" * 60)
        print("Running Demonstration Scenario")
        print("=" * 60 + "\n")
        
        # Create sample identities
        print("1. Creating sample identities...")
        
        id1, _ = self._central_command.create_identity(
            requesting_org_id=self._current_org_id,
            full_legal_name="James Thornbury",
            date_of_birth=date(1988, 7, 15),
            place_of_birth="Birmingham",
            nationality_at_birth="GBR",
            current_address="17 Maple Grove, Leeds LS1 4AB",
            contact_email="j.thornbury@email.co.uk",
            contact_phone="+447891234567",
            current_nationality="GBR",
        )
        print(f"   Created: {id1.identity_ref} - James Thornbury")
        
        id2, _ = self._central_command.create_identity(
            requesting_org_id=self._current_org_id,
            full_legal_name="Sarah Whitmore",
            date_of_birth=date(1992, 11, 3),
            place_of_birth="Edinburgh",
            nationality_at_birth="GBR",
            current_address="8 Castle View, Edinburgh EH1 2NG",
            contact_email="s.whitmore@email.co.uk",
            contact_phone="+447912345678",
            current_nationality="GBR",
        )
        print(f"   Created: {id2.identity_ref} - Sarah Whitmore")
        
        # Register organisations
        print("\n2. Registering consuming organisations...")
        
        hmrc = self._central_command.register_organisation(
            requesting_org_id=self._current_org_id,
            org_name="HMRC Tax Services",
            org_type=OrganisationType.TAX_AUTHORITY,
        )
        print(f"   Registered: {hmrc.org_id} - HMRC (Enhanced)")
        
        dvla = self._central_command.register_organisation(
            requesting_org_id=self._current_org_id,
            org_name="DVLA Licensing",
            org_type=OrganisationType.DRIVING_LICENCE_AUTHORITY,
        )
        print(f"   Registered: {dvla.org_id} - DVLA (Enhanced)")
        
        bank = self._central_command.register_organisation(
            requesting_org_id=self._current_org_id,
            org_name="Barclays Bank",
            org_type=OrganisationType.BANK,
        )
        print(f"   Registered: {bank.org_id} - Barclays (Basic)")
        
        # Demonstrate status changes
        print("\n3. Demonstrating status management...")
        self._central_command.suspend_identity(
            self._current_org_id, id2.identity_ref, "Verification required"
        )
        print(f"   Suspended: {id2.identity_ref}")
        
        self._central_command.reactivate_identity(
            self._current_org_id, id2.identity_ref, "Verification complete"
        )
        print(f"   Reactivated: {id2.identity_ref}")
        
        # Add restriction
        print("\n4. Adding temporary restriction...")
        self._central_command.add_restriction(
            requesting_org_id=self._current_org_id,
            identity_ref=id1.identity_ref,
            restriction_type="DRIVING_MEDICAL",
            effective_date=date.today(),
            description="Medical review required",
        )
        print(f"   Added DRIVING_MEDICAL restriction to {id1.identity_ref}")
        
        # Demonstrate verifications
        print("\n5. Performing verifications...")
        
        basic_result = self._portal.verify_basic(id1.identity_ref, bank.org_id)
        print(f"   Bank verification of {id1.identity_ref}: {basic_result.outcome.value}")
        
        tax_result = self._portal.verify_for_tax_period(
            id2.identity_ref,
            date(2024, 4, 6),
            date(2025, 4, 5),
            hmrc.org_id,
        )
        print(f"   HMRC verification of {id2.identity_ref}: {tax_result.outcome.value}")
        
        dvla_result = self._portal.verify_driving_eligibility(id1.identity_ref, dvla.org_id)
        print(f"   DVLA verification of {id1.identity_ref}: {dvla_result.outcome.value}")
        
        print("\n" + "=" * 60)
        print("Demonstration Complete!")
        print("Use 'stats' to see system overview, 'list-orgs' to see organisations")
        print("=" * 60 + "\n")

    def _cmd_help(self, args: str) -> None:
        """Display help information."""
        if args:
            cmd = args.strip().lower()
            if cmd in self._commands:
                # Show specific command help
                self._commands[cmd]("")
            else:
                self._print_error(f"Unknown command: {cmd}")
        else:
            print(self.HELP_TEXT)

    def _cmd_exit(self, args: str) -> None:
        """Exit the system."""
        print("\nThank you for using Nexus Digital ID System.")
        print("Goodbye!\n")
        sys.exit(0)
