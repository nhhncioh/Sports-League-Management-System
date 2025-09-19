#!/usr/bin/env python3
"""Test script for CLI commands."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def run_command(cmd, check=True):
    """Run a CLI command and return the result."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return e

def test_cli_commands():
    """Test all CLI commands."""
    print("=" * 60)
    print("TESTING CLI COMMANDS")
    print("=" * 60)

    # Set Flask app environment variable
    env = os.environ.copy()
    env['FLASK_APP'] = 'slms'

    # Test 1: Create organization
    print("\n1. Testing org:create command...")
    result = run_command("flask org:create --name 'Demo League' --slug demo --admin-email admin@demo.com --admin-password password123")

    # Test 2: List organizations
    print("\n2. Testing org:list command...")
    run_command("flask org:list")

    # Test 3: Get org info
    print("\n3. Testing org:info command...")
    run_command("flask org:info demo")

    # Test 4: Seed demo data
    print("\n4. Testing seed:demo command...")
    run_command("flask seed:demo --org demo --teams 6 --venues 2 --games 15")

    # Test 5: List seasons for export reference
    print("\n5. Testing export:list-seasons command...")
    result = run_command("flask export:list-seasons --org demo")

    # Extract season ID from output (simple parsing)
    season_id = None
    if result and result.stdout:
        for line in result.stdout.split('\n'):
            if 'ID:' in line:
                season_id = line.split('ID:')[1].strip()
                break

    if season_id:
        print(f"Found season ID: {season_id}")

        # Test 6: Export standings
        print("\n6. Testing export:season command (standings)...")
        run_command(f"flask export:season --season {season_id} --what standings")

        # Test 7: Export schedule
        print("\n7. Testing export:season command (schedule)...")
        run_command(f"flask export:season --season {season_id} --what schedule")

        # Test 8: Export registrations
        print("\n8. Testing export:season command (registrations)...")
        run_command(f"flask export:season --season {season_id} --what registrations")

        # Test 9: Export all
        print("\n9. Testing export:season command (all)...")
        run_command(f"flask export:season --season {season_id} --what all")

        # Test 10: Export teams
        print("\n10. Testing export:teams command...")
        run_command(f"flask export:teams --season {season_id}")
    else:
        print("Could not find season ID for export tests")

    # Test 11: Generate CSV templates
    print("\n11. Testing templates commands...")
    run_command("flask templates:teams")
    run_command("flask templates:players")
    run_command("flask templates:venues")

    # Test 12: Check generated files
    print("\n12. Checking generated files...")
    export_dir = Path('/tmp/exports')
    if export_dir.exists():
        files = list(export_dir.glob('*.csv'))
        print(f"Found {len(files)} CSV files in /tmp/exports:")
        for file in files:
            print(f"  • {file.name} ({file.stat().st_size} bytes)")
    else:
        print("Export directory not found")

    print("\n" + "=" * 60)
    print("CLI COMMAND TESTING COMPLETE")
    print("=" * 60)

    # Test 13: Verify organization can be accessed
    print("\n13. Organization URLs:")
    print("Public: http://localhost:5000/demo")
    print("Admin:  http://localhost:5000/demo/admin")

    print("\nTo test the public site:")
    print("1. Start the Flask app: flask run")
    print("2. Visit http://localhost:5000/demo")
    print("3. Login to admin at http://localhost:5000/demo/admin with:")
    print("   Email: admin@demo.com")
    print("   Password: password123")

if __name__ == "__main__":
    # Ensure we're in the right directory
    if not os.path.exists('slms'):
        print("Error: Please run this script from the project root directory")
        sys.exit(1)

    # Set FLASK_APP environment variable
    os.environ['FLASK_APP'] = 'slms'

    try:
        test_cli_commands()
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()