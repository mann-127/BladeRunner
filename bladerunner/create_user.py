#!/usr/bin/env python3
"""Utility to generate password hashes for BladeRunner JWT authentication."""

import sys
import getpass
import bcrypt


def main():
    """Generate bcrypt password hash for config.yml users."""
    print("BladeRunner User Creation Utility")
    print("=" * 50)
    print()

    username = input("Username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match")
        sys.exit(1)

    # Generate bcrypt hash
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    print()
    print("=" * 50)
    print("Add this entry to config.yml under api.auth.users:")
    print()
    print(f"  - username: {username}")
    print(f"    password_hash: {password_hash}")
    print(f"    user_id: {username}")
    print(f"    permissions: [\"read\", \"write\"]")
    print()
    print("=" * 50)


if __name__ == "__main__":
    main()
