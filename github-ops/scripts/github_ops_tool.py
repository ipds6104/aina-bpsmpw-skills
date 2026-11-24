#!/usr/bin/env python3
"""
github_ops_tool.py - Centralized GitHub Multi-Account & Infisical Sync Tool for Aina
Enables seamless token retrieval from Infisical Vault and account switching (ihkaru <-> ipds6104).
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

INFISICAL_DOMAIN = os.getenv("INFISICAL_DOMAIN", "https://secrets.dvlpid.my.id/api")
INFISICAL_CLIENT_ID = os.getenv("INFISICAL_CLIENT_ID", "d972328c-3c0c-4617-8c63-1cb1f7391f0f")
INFISICAL_CLIENT_SECRET = os.getenv("INFISICAL_CLIENT_SECRET", "")
if len(INFISICAL_CLIENT_SECRET) < 60:
    INFISICAL_CLIENT_SECRET = "1a73548b812589b6edf888ab64d8b0e52d615611feb7425ec75f5ea46017ae11"
INFISICAL_PROJECT_ID = os.getenv("INFISICAL_PROJECT_ID", "f13379e0-9661-4f8e-81ef-0e81d1502da1")
INFISICAL_ENV = os.getenv("INFISICAL_ENV", "dev")

GH_CONFIG_DIR = Path.home() / ".config" / "gh"
GH_HOSTS_FILE = GH_CONFIG_DIR / "hosts.yml"
GIT_CREDENTIALS_FILE = Path.home() / ".git-credentials"


def fetch_infisical_secrets() -> dict:
    """Fetch raw secrets from Infisical REST API via Universal Auth."""
    login_payload = json.dumps({
        "clientId": INFISICAL_CLIENT_ID,
        "clientSecret": INFISICAL_CLIENT_SECRET
    }).encode("utf-8")
    login_req = urllib.request.Request(
        f"{INFISICAL_DOMAIN}/v1/auth/universal-auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json", "User-Agent": "curl/8.0.0"}
    )
    with urllib.request.urlopen(login_req, timeout=10) as resp:
        token = json.loads(resp.read().decode())["accessToken"]

    sec_req = urllib.request.Request(
        f"{INFISICAL_DOMAIN}/v3/secrets/raw?environment={INFISICAL_ENV}&workspaceId={INFISICAL_PROJECT_ID}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "curl/8.0.0"}
    )
    with urllib.request.urlopen(sec_req, timeout=10) as resp:
        secrets_data = json.loads(resp.read().decode()).get("secrets", [])
        return {s["secretKey"]: s["secretValue"] for s in secrets_data}


def parse_hosts_yml(path: Path) -> dict:
    """Simple parser for gh hosts.yml format."""
    if not path.is_file():
        return {}
    content = path.read_text(encoding="utf-8")
    data = {"users": {}}
    current_user = None
    in_users = False

    for line in content.splitlines():
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue
        if line.startswith("    users:"):
            in_users = True
            continue
        if in_users and line.startswith("        ") and not line.startswith("            ") and line_strip.endswith(":"):
            current_user = line_strip[:-1]
            data["users"][current_user] = {}
            continue
        if in_users and current_user and line.startswith("            "):
            parts = line_strip.split(":", 1)
            if len(parts) == 2:
                data["users"][current_user][parts[0].strip()] = parts[1].strip()
            continue
        if not in_users or (in_users and not line.startswith("    ")):
            if not line.startswith(" "):
                in_users = False
            parts = line_strip.split(":", 1)
            if len(parts) == 2:
                data[parts[0].strip()] = parts[1].strip()

    return data


def write_hosts_yml(active_user: str, active_token: str, users: dict):
    """Write ~/.config/gh/hosts.yml with active user and all registered users."""
    GH_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "github.com:",
        f"    user: {active_user}",
        f"    oauth_token: {active_token}",
        "    git_protocol: https",
        "    users:"
    ]
    for u, u_data in users.items():
        tok = u_data.get("oauth_token", "")
        lines.append(f"        {u}:")
        lines.append(f"            oauth_token: {tok}")
    lines.append("")
    GH_HOSTS_FILE.write_text("\n".join(lines), encoding="utf-8")
    GH_HOSTS_FILE.chmod(0o600)

    # Sync git credential store and helper
    sync_git_credentials(active_user, active_token)


def sync_git_credentials(active_user: str, active_token: str):
    """Set up git credential helper and .git-credentials for transparent git push/pull."""
    GIT_CREDENTIALS_FILE.write_text(f"https://{active_user}:{active_token}@github.com\n", encoding="utf-8")
    GIT_CREDENTIALS_FILE.chmod(0o600)

    subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=False)
    subprocess.run(["gh", "auth", "setup-git"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_sync(args):
    """Sync GitHub credentials from Infisical Vault to local environment."""
    print("Connecting to Infisical Vault...")
    secrets = fetch_infisical_secrets()

    users = {}
    ihkaru_token = secrets.get("GH_TOKEN_IHKARU")
    if ihkaru_token:
        users["ihkaru"] = {"oauth_token": ihkaru_token}

    ipds_token = secrets.get("GH_TOKEN_IPDS6104")
    if ipds_token:
        users["ipds6104"] = {"oauth_token": ipds_token}

    # Fallback to general GH_TOKEN if needed
    gen_token = secrets.get("GH_TOKEN")
    gen_user = secrets.get("GH_USER", "ihkaru")
    if gen_token and gen_user not in users:
        users[gen_user] = {"oauth_token": gen_token}

    if not users:
        print(json.dumps({"status": "error", "message": "No GitHub tokens found in Infisical vault"}))
        sys.exit(1)

    # Check existing active user or default to ihkaru
    current = parse_hosts_yml(GH_HOSTS_FILE)
    active_user = current.get("user") or "ihkaru"
    if active_user not in users:
        active_user = list(users.keys())[0]

    active_token = users[active_user]["oauth_token"]
    write_hosts_yml(active_user, active_token, users)

    print(json.dumps({
        "status": "success",
        "message": f"Successfully synced GitHub credentials from Infisical Vault.",
        "active_user": active_user,
        "available_users": list(users.keys())
    }, indent=2))


def cmd_status(args):
    """Display current active GitHub account and available accounts."""
    if not GH_HOSTS_FILE.is_file():
        # Auto-sync if not present
        cmd_sync(args)
        return

    data = parse_hosts_yml(GH_HOSTS_FILE)
    active_user = data.get("user", "unknown")
    available_users = list(data.get("users", {}).keys())

    # Get gh auth status output
    gh_status = ""
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        gh_status = res.stdout or res.stderr
    except Exception:
        pass

    if args.json:
        print(json.dumps({
            "status": "success",
            "active_user": active_user,
            "available_users": available_users,
            "gh_status": gh_status.strip()
        }, indent=2))
        return

    print("=== GITHUB AUTH STATUS ===")
    print(f"• Active Account   : {active_user}")
    print(f"• Available Accounts: {', '.join(available_users)}")
    print(f"• Hosts Config     : {GH_HOSTS_FILE}")
    print(f"• Git Credentials  : {GIT_CREDENTIALS_FILE}")
    print("\n--- GitHub CLI (gh auth status) ---")
    for line in gh_status.splitlines()[:6]:
        print("  ", line)


def cmd_switch(args):
    """Switch active GitHub account between ihkaru and ipds6104."""
    target_user = args.user.lower().strip()
    data = parse_hosts_yml(GH_HOSTS_FILE)
    users = data.get("users", {})

    if target_user not in users:
        # Try fetching from Infisical first
        print(f"User '{target_user}' not in local config. Checking Infisical...")
        secrets = fetch_infisical_secrets()
        tok = secrets.get(f"GH_TOKEN_{target_user.upper()}") or (secrets.get("GH_TOKEN") if secrets.get("GH_USER") == target_user else None)
        if tok:
            users[target_user] = {"oauth_token": tok}
        else:
            print(json.dumps({
                "status": "error",
                "message": f"User '{target_user}' not found in Infisical or local config. Available: {list(users.keys())}"
            }))
            sys.exit(1)

    target_token = users[target_user]["oauth_token"]
    write_hosts_yml(target_user, target_token, users)

    print(json.dumps({
        "status": "success",
        "message": f"Switched active GitHub account to '{target_user}'.",
        "active_user": target_user,
        "available_users": list(users.keys())
    }, indent=2))


def cmd_whoami(args):
    """Display active username only."""
    data = parse_hosts_yml(GH_HOSTS_FILE)
    print(data.get("user", "unknown"))


def main():
    parser = argparse.ArgumentParser(description="Aina GitHub Multi-Account & Infisical Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync
    subparsers.add_parser("sync", help="Sync tokens from Infisical Vault to hosts.yml and git credentials")

    # status
    p_status = subparsers.add_parser("status", help="Show current GitHub auth status and available accounts")
    p_status.add_argument("--json", action="store_true", help="Output JSON format")

    # switch
    p_switch = subparsers.add_parser("switch", help="Switch active GitHub account (e.g., ihkaru or ipds6104)")
    p_switch.add_argument("user", choices=["ihkaru", "ipds6104"], help="Username to switch to")

    # whoami
    subparsers.add_parser("whoami", help="Print active GitHub username")

    args = parser.parse_args()
    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "switch":
        cmd_switch(args)
    elif args.command == "whoami":
        cmd_whoami(args)


if __name__ == "__main__":
    main()
