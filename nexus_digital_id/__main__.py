"""
Nexus Digital ID - Main Entry Point

Run the system with: python -m nexus_digital_id
"""

import sys
import argparse

from nexus_digital_id.interface.command_deck import CommandDeck


def main():
    """Main entry point for the Nexus Digital ID system."""
    parser = argparse.ArgumentParser(
        description="Nexus Digital Identity Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m nexus_digital_id                    # Interactive mode
  python -m nexus_digital_id --demo             # Run demonstration
  python -m nexus_digital_id --command "stats"  # Single command
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration scenario and exit"
    )
    
    parser.add_argument(
        "--command", "-c",
        type=str,
        help="Execute a single command and exit"
    )
    
    args = parser.parse_args()
    
    deck = CommandDeck()
    
    if args.demo:
        deck._cmd_demo("")
        return 0
    
    if args.command:
        deck._process_command(args.command)
        return 0
    
    # Interactive mode
    deck.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
