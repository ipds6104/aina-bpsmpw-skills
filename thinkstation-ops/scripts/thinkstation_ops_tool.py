#!/usr/bin/env python3
"""
thinkstation_ops_tool.py - Host & Container Management CLI for Lenovo ThinkStation P320
Provides remote execution, Docker container operations, and host observability via SSH.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

DEFAULT_TAILSCALE_HOST = "100.101.49.42"
DEFAULT_LAN_HOST = "192.168.0.136"
DEFAULT_USER = "server"
DEFAULT_PORT = 22
KEY_FILE = Path.home() / ".ssh" / "id_ed25519_thinkstation"
CONFIG_FILE = Path.home() / ".ssh" / "config"

INFISICAL_DOMAIN = os.getenv("INFISICAL_DOMAIN", "https://secrets.dvlpid.my.id/api")
INFISICAL_CLIENT_ID = os.getenv("INFISICAL_CLIENT_ID", "d972328c-3c0c-4617-8c63-1cb1f7391f0f")
INFISICAL_CLIENT_SECRET = os.getenv("INFISICAL_CLIENT_SECRET", "")
if len(INFISICAL_CLIENT_SECRET) < 60:
    INFISICAL_CLIENT_SECRET = "1a73548b812589b6edf888ab64d8b0e52d615611feb7425ec75f5ea46017ae11"
INFISICAL_PROJECT_ID = os.getenv("INFISICAL_PROJECT_ID", "f13379e0-9661-4f8e-81ef-0e81d1502da1")
INFISICAL_ENV = os.getenv("INFISICAL_ENV", "dev")


def ensure_ssh_client():
    """Ensure openssh-client binary is installed."""
    if not shutil.which("ssh"):
        try:
            subprocess.run(["apt-get", "update"], capture_output=True, check=True)
            subprocess.run(["apt-get", "install", "-y", "openssh-client"], capture_output=True, check=True)
        except Exception as e:
            raise RuntimeError(f"Failed to install openssh-client: {e}")


def ensure_ssh_auth() -> dict:
    """Ensure SSH key exists from Infisical and SSH config is populated."""
    ensure_ssh_client()

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    ssh_dir.chmod(0o700)

    if not KEY_FILE.is_file() or KEY_FILE.stat().st_size == 0:
        # Fetch private key from Infisical REST API
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
            sec_dict = {s["secretKey"]: s["secretValue"] for s in secrets_data}

        priv_key = sec_dict.get("SERVER_SSH_PRIVATE_KEY")
        if not priv_key:
            raise RuntimeError("SERVER_SSH_PRIVATE_KEY not found in Infisical vault")

        KEY_FILE.write_text(priv_key.strip() + "\n")
        KEY_FILE.chmod(0o600)

    # Ensure config entry
    config_entry = (
        "Host thinkstation\n"
        f"    HostName {DEFAULT_TAILSCALE_HOST}\n"
        f"    User {DEFAULT_USER}\n"
        f"    Port {DEFAULT_PORT}\n"
        f"    IdentityFile {KEY_FILE}\n"
        "    StrictHostKeyChecking no\n"
        "    BatchMode yes\n"
        "    ConnectTimeout 5\n\n"
        "Host thinkstation-lan\n"
        f"    HostName {DEFAULT_LAN_HOST}\n"
        f"    User {DEFAULT_USER}\n"
        f"    Port {DEFAULT_PORT}\n"
        f"    IdentityFile {KEY_FILE}\n"
        "    StrictHostKeyChecking no\n"
        "    BatchMode yes\n"
        "    ConnectTimeout 5\n"
    )

    if not CONFIG_FILE.is_file() or "thinkstation" not in CONFIG_FILE.read_text():
        with open(CONFIG_FILE, "a") as f:
            f.write("\n" + config_entry)
        CONFIG_FILE.chmod(0o600)

    return {
        "status": "success",
        "key_path": str(KEY_FILE),
        "target_host": DEFAULT_TAILSCALE_HOST,
        "user": DEFAULT_USER,
    }


def run_remote_ssh(command: str, use_sudo: bool = False, timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute command over SSH on ThinkStation."""
    ensure_ssh_auth()
    full_cmd = f"sudo {command}" if use_sudo else command
    ssh_args = [
        "ssh",
        "thinkstation",
        full_cmd
    ]
    return subprocess.run(ssh_args, capture_output=True, text=True, timeout=timeout)


def cmd_status(args):
    """Check host specs, uptime, load averages, memory, and disk usage."""
    probe_script = (
        "echo '===HOST===' && hostname && "
        "echo '===UPTIME===' && uptime && "
        "echo '===MEM===' && free -m && "
        "echo '===DISK===' && df -h / && "
        "echo '===CONTAINERS===' && sudo docker ps -q | wc -l"
    )
    res = run_remote_ssh(probe_script)
    if res.returncode != 0:
        print(json.dumps({
            "status": "error",
            "message": res.stderr.strip() or "SSH connection failed"
        }, indent=2))
        sys.exit(1)

    sections = {}
    current_key = None
    for line in res.stdout.splitlines():
        if line.startswith("===") and line.endswith("==="):
            current_key = line.strip("=").lower()
            sections[current_key] = []
        elif current_key:
            sections[current_key].append(line)

    host_name = sections.get("host", ["unknown"])[0].strip()
    uptime_str = sections.get("uptime", ["unknown"])[0].strip()
    container_count = sections.get("containers", ["0"])[0].strip()

    mem_lines = sections.get("mem", [])
    ram_info = {}
    if len(mem_lines) >= 2:
        parts = mem_lines[1].split()
        if len(parts) >= 7:
            ram_info = {
                "total_mb": int(parts[1]),
                "used_mb": int(parts[2]),
                "free_mb": int(parts[3]),
                "available_mb": int(parts[6]),
            }

    disk_lines = sections.get("disk", [])
    disk_info = {}
    if len(disk_lines) >= 2:
        parts = disk_lines[1].split()
        if len(parts) >= 5:
            disk_info = {
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "use_percent": parts[4],
            }

    result = {
        "status": "success",
        "host": host_name,
        "tailscale_ip": DEFAULT_TAILSCALE_HOST,
        "uptime": uptime_str,
        "running_containers": int(container_count) if container_count.isdigit() else 0,
        "ram": ram_info,
        "disk": disk_info
    }

    if getattr(args, "markdown", False):
        print(f"*Status Host ThinkStation P320*\n"
              f"• *Hostname:* `{host_name}`\n"
              f"• *Uptime & Load:* {uptime_str}\n"
              f"• *Container Berjalan:* {result['running_containers']} container\n"
              f"• *RAM:* Terpakai {ram_info.get('used_mb', 0)}MB / Total {ram_info.get('total_mb', 0)}MB\n"
              f"• *Disk Root (/):* Sisa {disk_info.get('avail', '-')} dari {disk_info.get('size', '-')} ({disk_info.get('use_percent', '-')})")
    else:
        print(json.dumps(result, indent=2))


def cmd_docker_ps(args):
    """List containers on the ThinkStation host."""
    all_flag = "-a" if getattr(args, "all", False) else ""
    format_arg = '{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'
    cmd = f"sudo docker ps {all_flag} --format '{format_arg}'"
    res = run_remote_ssh(cmd)

    if res.returncode != 0:
        print(json.dumps({"status": "error", "message": res.stderr.strip()}, indent=2))
        sys.exit(1)

    containers = []
    filter_kw = (args.filter or "").lower()
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        name = parts[0] if len(parts) > 0 else ""
        status = parts[1] if len(parts) > 1 else ""
        image = parts[2] if len(parts) > 2 else ""
        ports = parts[3] if len(parts) > 3 else ""

        if filter_kw and (filter_kw not in name.lower() and filter_kw not in image.lower()):
            continue

        containers.append({
            "name": name,
            "status": status,
            "image": image,
            "ports": ports
        })

    if getattr(args, "markdown", False):
        if not containers:
            print(f"Tidak ada container yang cocok dengan filter '{filter_kw}'.")
            return
        lines = [f"*Daftar Container ThinkStation ({len(containers)} aktif):*"]
        for c in containers:
            lines.append(f"• *{c['name']}*: `{c['status']}`")
        print("\n".join(lines))
    else:
        print(json.dumps({
            "status": "success",
            "total": len(containers),
            "containers": containers
        }, indent=2))


def cmd_docker_logs(args):
    """Fetch logs for a container."""
    tail = args.tail or 50
    grep_filter = f" | grep -i '{args.grep}'" if args.grep else ""
    cmd = f"sudo docker logs --tail {tail} {args.name} 2>&1{grep_filter}"
    res = run_remote_ssh(cmd)

    output = res.stdout.strip() or res.stderr.strip()
    if getattr(args, "markdown", False):
        print(f"*Log Container `{args.name}` (tail {tail}):*\n```\n{output[-1500:]}\n```")
    else:
        print(json.dumps({
            "status": "success",
            "container": args.name,
            "tail": tail,
            "output": output
        }, indent=2))


def cmd_docker_restart(args):
    """Restart a container on the host."""
    target = args.name.lower()
    my_container = os.getenv("COOLIFY_CONTAINER_NAME", "").lower()
    my_uuid = os.getenv("COOLIFY_RESOURCE_UUID", "").lower()
    if target.startswith("aina") or (my_container and target in my_container) or (my_uuid and my_uuid in target):
        print(json.dumps({
            "status": "error",
            "message": f"Safety Guardrail: Dilarang merestart/menghentikan container Aina sendiri ('{args.name}') agar tidak mati/terputus!"
        }, indent=2))
        sys.exit(1)

    cmd = f"sudo docker restart {args.name}"
    res = run_remote_ssh(cmd)
    if res.returncode == 0:
        print(json.dumps({
            "status": "success",
            "message": f"Container '{args.name}' successfully restarted.",
            "container": args.name
        }, indent=2))
    else:
        print(json.dumps({
            "status": "error",
            "message": res.stderr.strip() or res.stdout.strip()
        }, indent=2))
        sys.exit(1)


def cmd_exec(args):
    """Execute arbitrary command on ThinkStation."""
    timeout = getattr(args, 'timeout', 30)
    res = run_remote_ssh(args.cmd, use_sudo=args.sudo, timeout=timeout)
    print(json.dumps({
        "status": "success" if res.returncode == 0 else "error",
        "returncode": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr
    }, indent=2))


def cmd_ensure_auth(args):
    """Ensure SSH keys and authentication are present."""
    res = ensure_ssh_auth()
    print(json.dumps(res, indent=2))


def main():
    parser = argparse.ArgumentParser(description="ThinkStation P320 Ops Helper")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_status = subparsers.add_parser("status", help="Get host status & hardware metrics")
    p_status.add_argument("-m", "--markdown", action="store_true", help="Print WhatsApp-friendly Markdown")
    p_status.set_defaults(func=cmd_status)

    p_ps = subparsers.add_parser("docker-ps", help="List Docker containers on host")
    p_ps.add_argument("-a", "--all", action="store_true", help="Include stopped containers")
    p_ps.add_argument("-f", "--filter", type=str, default="", help="Filter by container name or image")
    p_ps.add_argument("-m", "--markdown", action="store_true", help="Print WhatsApp-friendly Markdown")
    p_ps.set_defaults(func=cmd_docker_ps)

    p_logs = subparsers.add_parser("docker-logs", help="Get container logs")
    p_logs.add_argument("name", help="Container name")
    p_logs.add_argument("--tail", type=int, default=50, help="Number of lines from end")
    p_logs.add_argument("--grep", type=str, default="", help="Filter log lines")
    p_logs.add_argument("-m", "--markdown", action="store_true", help="Print WhatsApp-friendly Markdown")
    p_logs.set_defaults(func=cmd_docker_logs)

    p_restart = subparsers.add_parser("docker-restart", help="Restart a container")
    p_restart.add_argument("name", help="Container name to restart")
    p_restart.set_defaults(func=cmd_docker_restart)

    p_exec = subparsers.add_parser("exec", help="Execute command on host")
    p_exec.add_argument("cmd", help="Command string to run")
    p_exec.add_argument("--sudo", action="store_true", help="Run with sudo privileges")
    p_exec.add_argument("--timeout", type=int, default=60, help="SSH command timeout in seconds")
    p_exec.set_defaults(func=cmd_exec)

    p_auth = subparsers.add_parser("ensure-auth", help="Setup SSH authentication keys")
    p_auth.set_defaults(func=cmd_ensure_auth)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
