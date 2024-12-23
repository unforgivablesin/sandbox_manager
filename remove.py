#!/usr/bin/env python3
"""
SandboxManager removal script.
Safely removes sandboxed applications and their configurations.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

def validate_app_name(name: str) -> str:
    """Validate application name"""
    if not name or not name.replace('-', '').replace('_', '').isalnum():
        raise argparse.ArgumentTypeError(f"Invalid application name: {name}")
    return name

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description='Sandbox tool removal',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--app', required=True, type=validate_app_name,
                       help='Name of the sandboxed application to remove')
    
    return parser

def confirm_removal(app_name: str) -> bool:
    """Ask for confirmation before removing the application"""
    try:
        response = input(f"Are you sure you want to remove '{app_name}'? [y/N] ").lower()
        return response in ('y', 'yes')
    except (KeyboardInterrupt, EOFError):
        return False

def main() -> int:
    """Main entry point"""
    try:
        parser = create_parser()
        args = parser.parse_args()

        # Print warning with color
        print(f"Deleting application '\x1b[91m{args.app}\x1b[0m'")

        # Ask for confirmation
        if not confirm_removal(args.app):
            print("Operation cancelled")
            return 0

        # Import here to avoid overhead if argument parsing fails
        from src.sandbox import sandbox_delete_app
        sandbox_delete_app(args.app)
        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
