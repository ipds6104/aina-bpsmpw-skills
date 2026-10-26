#!/usr/bin/env python3
"""
coolify_ops_tool.py - Universal Coolify Operations CLI for ThinkStation P320
Provides comprehensive application, service, environment variable, deployment,
and container lifecycle management across all resources hosted in Coolify.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Import remote execution from thinkstation-ops
THINKSTATION_OPS_PATH = Path("/app/data/custom-skills/thinkstation-ops/scripts")
if str(THINKSTATION_OPS_PATH) not in sys.path:
    sys.path.insert(0, str(THINKSTATION_OPS_PATH))

try:
    from thinkstation_ops_tool import run_remote_ssh
except ImportError:
    fallback_path = Path(__file__).resolve().parent.parent.parent / "thinkstation-ops" / "scripts"
    if str(fallback_path) not in sys.path:
        sys.path.insert(0, str(fallback_path))
    from thinkstation_ops_tool import run_remote_ssh


def run_coolify_tinker(php_code: str, timeout: int = 40):
    """Execute PHP code inside the Coolify container via artisan tinker."""
    clean_code = php_code.replace("'", "'\\''")
    remote_cmd = f"docker exec coolify php artisan tinker --execute='{clean_code}'"
    return run_remote_ssh(remote_cmd, timeout=timeout)


def run_coolify_psql(sql: str, timeout: int = 30):
    """Execute SQL query inside coolify-db PostgreSQL container."""
    clean_sql = sql.replace("'", "'\\''")
    remote_cmd = f"docker exec coolify-db psql -U coolify -d coolify -c '{clean_sql}'"
    return run_remote_ssh(remote_cmd, timeout=timeout)


def resolve_application(target: str) -> dict:
    """Resolve application by ID, UUID, name, or git repository."""
    tinker_script = f"""
    $target = '{target}';
    $app = is_numeric($target) ? App\\Models\\Application::find($target) : null;
    if (!$app) $app = App\\Models\\Application::where('uuid', $target)->first();
    if (!$app) $app = App\\Models\\Application::where('name', 'like', "%$target%")->orWhere('git_repository', 'like', "%$target%")->first();
    if ($app) {{
        echo json_encode([
            'found' => true,
            'id' => $app->id,
            'uuid' => $app->uuid,
            'name' => $app->name,
            'git_repository' => $app->git_repository,
            'git_branch' => $app->git_branch,
            'status' => $app->status,
            'fqdn' => $app->fqdn,
        ]);
    }} else {{
        echo json_encode(['found' => false]);
    }}
    """
    res = run_coolify_tinker(tinker_script)
    if res.returncode != 0:
        raise RuntimeError(f"Gagal resolve aplikasi: {res.stderr.strip() or res.stdout.strip()}")

    try:
        data = json.loads(res.stdout.strip())
        if not data.get("found"):
            raise ValueError(f"Aplikasi dengan identifier '{target}' tidak ditemukan di Coolify.")
        return data
    except json.JSONDecodeError:
        raise ValueError(f"Output tidak valid dari Coolify: {res.stdout.strip()}")


def cmd_apps(args):
    """List all applications in Coolify."""
    filter_sql = ""
    if args.filter:
        kw = args.filter.replace("'", "''")
        filter_sql = f"WHERE name ILIKE '%{kw}%' OR git_repository ILIKE '%{kw}%' OR uuid ILIKE '%{kw}%'"

    sql = f"""
    SELECT id, name, uuid, git_repository, git_branch, status
    FROM applications
    {filter_sql}
    ORDER BY id ASC;
    """
    res = run_coolify_psql(sql)
    if res.returncode != 0:
        print(f"Error querying applications: {res.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        # Query structured data via tinker
        tinker_script = f"""
        $q = App\\Models\\Application::query();
        $f = '{args.filter or ""}';
        if ($f) $q->where('name', 'like', "%$f%")->orWhere('git_repository', 'like', "%$f%");
        echo json_encode($q->orderBy('id')->get()->map(fn($a) => [
            'id' => $a->id,
            'uuid' => $a->uuid,
            'name' => $a->name,
            'git_repository' => $a->git_repository,
            'git_branch' => $a->git_branch,
            'status' => $a->status,
            'fqdn' => $a->fqdn,
        ]));
        """
        res_json = run_coolify_tinker(tinker_script)
        print(res_json.stdout.strip())
        return

    print("=== DAFTAR APLIKASI DI COOLIFY (THINKSTATION) ===")
    print(res.stdout.strip())


def cmd_services(args):
    """List one-click services (n8n, windmill, phpmyadmin, etc.)."""
    sql = "SELECT id, name, uuid, service_type FROM services ORDER BY id ASC;"
    res = run_coolify_psql(sql)
    print("=== DAFTAR SERVICES DI COOLIFY ===")
    print(res.stdout.strip())


def cmd_projects(args):
    """List all projects in Coolify."""
    sql = "SELECT id, name, uuid, description FROM projects ORDER BY id ASC;"
    res = run_coolify_psql(sql)
    print("=== DAFTAR PROJECT DI COOLIFY ===")
    print(res.stdout.strip())


def cmd_status(args):
    """Check status of a specific application or global Coolify overview."""
    if not args.app:
        # Global overview
        sql_summary = """
        SELECT status, count(*) AS total
        FROM applications
        GROUP BY status ORDER BY total DESC;
        """
        res_sum = run_coolify_psql(sql_summary)
        res_running = run_remote_ssh("docker ps -q | wc -l")

        print("=== RINGKASAN COOLIFY DI THINKSTATION ===")
        print(f"Total Container Docker Aktif di Host: {res_running.stdout.strip()}")
        print("\nDistribusi Status Aplikasi Coolify:")
        print(res_sum.stdout.strip())
        print("\nTip: Gunakan --app <nama|id|uuid> untuk status mendalam suatu aplikasi.")
        return

    app = resolve_application(args.app)
    app_id = app["id"]
    app_uuid = app["uuid"]

    # 1. Docker container host
    res_docker = run_remote_ssh(
        f"docker ps -a --filter 'name={app_uuid}' --format '{{{{.ID}}}}|{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Ports}}}}'"
    )

    # 2. Latest 3 deployments
    sql_deploy = (
        f"SELECT id, status, commit, created_at, updated_at "
        f"FROM application_deployment_queues WHERE application_id = '{app_id}' "
        f"ORDER BY id DESC LIMIT 3;"
    )
    res_deploy = run_coolify_psql(sql_deploy)

    if args.json:
        print(json.dumps({
            "status": "success",
            "app": app,
            "containers": res_docker.stdout.strip().splitlines() if res_docker.stdout else [],
            "deployments": res_deploy.stdout.strip()
        }, indent=2))
        return

    print(f"=== STATUS APLIKASI: {app['name']} (ID: {app_id}) ===")
    print(f"• UUID: {app_uuid}")
    print(f"• Repository: {app['git_repository']} (branch: {app['git_branch']})")
    print(f"• Status Coolify: {app['status']}")
    if app.get("fqdn"):
        print(f"• FQDN: {app['fqdn']}")

    print("\n=== CONTAINER DOCKER HOST ===")
    if res_docker.stdout.strip():
        for line in res_docker.stdout.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                print(f"• Container: {parts[1]} | Status: {parts[2]} | ID: {parts[0]}")
    else:
        print("Tidak ada container berjalan yang cocok.")

    print("\n=== RIWAYAT DEPLOYMENT TERAKHIR ===")
    print(res_deploy.stdout.strip())


def cmd_get_env(args):
    """List or inspect environment variables for any application."""
    app = resolve_application(args.app)
    app_id = app["id"]

    tinker_script = f"""
    $app = App\\Models\\Application::find({app_id});
    $query = $app->environment_variables();
    $filter = '{args.filter or ""}';
    if ($filter) {{
        $query->where('key', 'like', "%$filter%");
    }}
    $vars = $query->orderBy('key')->get()->map(function($v) {{
        return [
            'id' => $v->id,
            'key' => $v->key,
            'value' => $v->value,
            'is_runtime' => (bool)$v->is_runtime,
            'is_buildtime' => (bool)$v->is_buildtime,
            'updated_at' => (string)$v->updated_at,
        ];
    }});
    echo json_encode($vars);
    """
    res = run_coolify_tinker(tinker_script)
    if res.returncode != 0:
        print(f"Error executing tinker: {res.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(res.stdout.strip())
    except json.JSONDecodeError:
        print(f"Output raw:\n{res.stdout.strip()}")
        return

    if args.json:
        print(json.dumps(data, indent=2))
        return

    print(f"=== ENVIRONMENT VARIABLES: {app['name']} (Total: {len(data)}) ===")
    for item in data:
        key = item['key']
        val = item['value'] or ''
        if not args.show_values and any(s in key.lower() for s in ['key', 'secret', 'password', 'token']):
            val_masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "********"
        else:
            val_masked = val
        print(f"• {key} = {val_masked} (runtime: {item['is_runtime']}, buildtime: {item['is_buildtime']})")


def cmd_set_env(args):
    """Set or update an environment variable for any application."""
    app = resolve_application(args.app)
    app_id = app["id"]
    key = args.key.strip()
    val = args.value.strip()
    is_runtime = "true" if not args.no_runtime else "false"
    is_buildtime = "true" if args.buildtime else "false"

    tinker_script = f"""
    $app = App\\Models\\Application::find({app_id});
    $env = $app->environment_variables()->where('key', '{key}')->first();
    if ($env) {{
        $env->update([
            'value' => '{val}',
            'is_runtime' => {is_runtime},
            'is_buildtime' => {is_buildtime},
        ]);
        echo "UPDATED";
    }} else {{
        $app->environment_variables()->create([
            'key' => '{key}',
            'value' => '{val}',
            'is_runtime' => {is_runtime},
            'is_buildtime' => {is_buildtime},
        ]);
        echo "CREATED";
    }}
    """
    res = run_coolify_tinker(tinker_script)
    if res.returncode != 0 or ("UPDATED" not in res.stdout and "CREATED" not in res.stdout):
        print(f"Gagal mengatur variabel: {res.stderr.strip() or res.stdout.strip()}", file=sys.stderr)
        sys.exit(1)

    action = "diperbarui" if "UPDATED" in res.stdout else "dibuat"
    print(f"Variabel '{key}' berhasil {action} untuk aplikasi '{app['name']}' (ID: {app_id}).")

    if args.redeploy:
        cmd_deploy(argparse.Namespace(app=args.app, force_rebuild=False))


def cmd_del_env(args):
    """Delete an environment variable from an application."""
    app = resolve_application(args.app)
    app_id = app["id"]
    key = args.key.strip()

    tinker_script = f"""
    $app = App\\Models\\Application::find({app_id});
    $env = $app->environment_variables()->where('key', '{key}')->first();
    if ($env) {{
        $env->delete();
        echo "DELETED";
    }} else {{
        echo "NOT_FOUND";
    }}
    """
    res = run_coolify_tinker(tinker_script)
    if "DELETED" in res.stdout:
        print(f"Variabel '{key}' berhasil dihapus dari aplikasi '{app['name']}'.")
    elif "NOT_FOUND" in res.stdout:
        print(f"Variabel '{key}' tidak ditemukan di aplikasi '{app['name']}'.")
    else:
        print(f"Error: {res.stderr.strip() or res.stdout.strip()}", file=sys.stderr)
        sys.exit(1)


def cmd_deploy(args):
    """Trigger deployment for any application in Coolify."""
    app = resolve_application(args.app)
    app_id = app["id"]
    force_rebuild = "true" if getattr(args, "force_rebuild", False) else "false"

    tinker_script = f"""
    $app = App\\Models\\Application::find({app_id});
    $deployment_uuid = (string) new Visus\\Cuid2\\Cuid2;
    $res = queue_application_deployment(
        application: $app,
        deployment_uuid: $deployment_uuid,
        force_rebuild: {force_rebuild}
    );
    echo json_encode([
        'deployment_uuid' => $deployment_uuid,
        'result' => $res
    ]);
    """
    res = run_coolify_tinker(tinker_script)
    if res.returncode != 0:
        print(f"Gagal memicu deployment: {res.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    print(f"Deployment untuk '{app['name']}' (ID: {app_id}) berhasil dimasukkan ke antrean Coolify:")
    print(res.stdout.strip())


def cmd_restart(args):
    """Restart running container(s) for an application on ThinkStation."""
    app = resolve_application(args.app)
    app_uuid = app["uuid"]

    find_cmd = f"docker ps --filter 'name={app_uuid}' -q"
    res = run_remote_ssh(find_cmd)
    container_ids = res.stdout.strip().splitlines()
    if not container_ids:
        print(f"Tidak ada container aktif yang cocok dengan UUID aplikasi '{app['name']}' ({app_uuid}).", file=sys.stderr)
        sys.exit(1)

    for cid in container_ids:
        restart_cmd = f"docker restart {cid}"
        res_restart = run_remote_ssh(restart_cmd)
        if res_restart.returncode == 0:
            print(f"Container {cid} ({app['name']}) berhasil di-restart.")
        else:
            print(f"Gagal restart container {cid}: {res_restart.stderr.strip()}", file=sys.stderr)


def cmd_logs(args):
    """Fetch logs from running container or Coolify deployment queue."""
    app = resolve_application(args.app)
    app_id = app["id"]
    app_uuid = app["uuid"]

    if args.deployment:
        tinker_script = f"""
        $q = App\\Models\\ApplicationDeploymentQueue::where('application_id', '{app_id}')->orderBy('id', 'desc')->first();
        if ($q) {{
            echo "DEPLOYMENT ID: " . $q->id . " | STATUS: " . $q->status . "\\n";
            echo substr($q->logs, -{args.tail * 60});
        }} else {{
            echo "No deployment found for application {app_id}";
        }}
        """
        res = run_coolify_tinker(tinker_script)
        print(res.stdout.strip())
    else:
        find_cmd = f"docker ps --filter 'name={app_uuid}' -q"
        res = run_remote_ssh(find_cmd)
        container_ids = res.stdout.strip().splitlines()
        if not container_ids:
            print(f"Container aktif untuk '{app['name']}' tidak ditemukan.", file=sys.stderr)
            sys.exit(1)
        cid = container_ids[0]
        res_logs = run_remote_ssh(f"docker logs --tail {args.tail} {cid}")
        print(res_logs.stdout.strip() or res_logs.stderr.strip())


def cmd_sync_aina_wa(args):
    """Helper: sync Aina WhatsApp provider credentials to an application (default: sipedas)."""
    target_app = args.app or "sipedas"
    app = resolve_application(target_app)
    app_id = app["id"]

    base_url = args.base_url or os.getenv("WHATSMEOW_BASE_URL", "https://aina-wa.dvlpid.my.id")
    api_key = args.api_key or os.getenv("WHATSMEOW_API_KEY", "")

    if not api_key:
        print("Error: WHATSMEOW_API_KEY tidak ditemukan di environment.", file=sys.stderr)
        sys.exit(1)

    tinker_script = f"""
    $app = App\\Models\\Application::find({app_id});
    $vars = [
        'WHATSAPP_PROVIDER' => 'aina',
        'WHATSMEOW_BASE_URL' => '{base_url}',
        'WHATSMEOW_API_KEY' => '{api_key}',
    ];
    foreach ($vars as $k => $v) {{
        $env = $app->environment_variables()->where('key', $k)->first();
        if ($env) {{
            $env->update(['value' => $v, 'is_runtime' => true, 'is_buildtime' => false]);
        }} else {{
            $app->environment_variables()->create(['key' => $k, 'value' => $v, 'is_runtime' => true, 'is_buildtime' => false]);
        }}
    }}
    echo "SYNC_SUCCESS";
    """
    res = run_coolify_tinker(tinker_script)
    if "SYNC_SUCCESS" not in res.stdout:
        print(f"Gagal sinkronisasi WhatsApp ke '{app['name']}': {res.stderr.strip() or res.stdout.strip()}", file=sys.stderr)
        sys.exit(1)

    print(f"Berhasil menyinkronkan kredensial WhatsApp Aina ke '{app['name']}' (ID: {app_id}):")
    print("• WHATSAPP_PROVIDER = aina")
    print(f"• WHATSMEOW_BASE_URL = {base_url}")
    print(f"• WHATSMEOW_API_KEY = {api_key[:6]}...{api_key[-4:]}")

    if args.redeploy:
        print(f"\nMemulai trigger deployment '{app['name']}'...")
        cmd_deploy(argparse.Namespace(app=target_app, force_rebuild=args.force_rebuild))


def cmd_deployments(args):
    """List recent deployments across all applications or for a specific app."""
    where_sql = ""
    if args.app:
        app = resolve_application(args.app)
        where_sql = f"WHERE application_id = '{app['id']}'"

    sql = f"""
    SELECT id, application_id, status, commit, created_at, updated_at
    FROM application_deployment_queues
    {where_sql}
    ORDER BY id DESC LIMIT {args.limit};
    """
    res = run_coolify_psql(sql)
    print("=== ANTREAN DEPLOYMENT TERAKHIR COOLIFY ===")
    print(res.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="Universal Coolify Operations CLI for ThinkStation P320")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # apps
    p_apps = subparsers.add_parser("apps", help="Daftar seluruh aplikasi di Coolify")
    p_apps.add_argument("--filter", help="Filter berdasarkan nama, repo, atau UUID")
    p_apps.add_argument("--json", action="store_true", help="Output format JSON")
    p_apps.set_defaults(func=cmd_apps)

    # services
    p_svc = subparsers.add_parser("services", help="Daftar layanan one-click (n8n, windmill, phpmyadmin, dsb.)")
    p_svc.set_defaults(func=cmd_services)

    # projects
    p_prj = subparsers.add_parser("projects", help="Daftar proyek di Coolify")
    p_prj.set_defaults(func=cmd_projects)

    # status
    p_status = subparsers.add_parser("status", help="Cek status aplikasi atau ringkasan sistem Coolify")
    p_status.add_argument("--app", help="Nama, ID, atau UUID aplikasi spesifik")
    p_status.add_argument("--json", action="store_true", help="Output format JSON")
    p_status.set_defaults(func=cmd_status)

    # get-env
    p_getenv = subparsers.add_parser("get-env", help="Lihat environment variables suatu aplikasi")
    p_getenv.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi (contoh: sipedas, aina, 10)")
    p_getenv.add_argument("--filter", help="Filter nama variabel")
    p_getenv.add_argument("--show-values", action="store_true", help="Tampilkan nilai rahasia tanpa masking")
    p_getenv.add_argument("--json", action="store_true", help="Output format JSON")
    p_getenv.set_defaults(func=cmd_get_env)

    # set-env
    p_setenv = subparsers.add_parser("set-env", help="Setel atau perbarui environment variable aplikasi")
    p_setenv.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi (contoh: sipedas, aina, 10)")
    p_setenv.add_argument("key", help="Nama variabel environment (contoh: LOG_LEVEL)")
    p_setenv.add_argument("value", help="Nilai variabel")
    p_setenv.add_argument("--buildtime", action="store_true", help="Tandai sebagai build-time variable")
    p_setenv.add_argument("--no-runtime", action="store_true", help="Nonaktifkan runtime variable")
    p_setenv.add_argument("--redeploy", action="store_true", help="Langsung trigger deployment setelah simpan")
    p_setenv.set_defaults(func=cmd_set_env)

    # del-env
    p_delenv = subparsers.add_parser("del-env", help="Hapus environment variable dari aplikasi")
    p_delenv.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi")
    p_delenv.add_argument("key", help="Nama variabel yang ingin dihapus")
    p_delenv.set_defaults(func=cmd_del_env)

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Picu proses build & deployment aplikasi di Coolify")
    p_deploy.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi")
    p_deploy.add_argument("--force-rebuild", action="store_true", help="Paksa docker build tanpa cache")
    p_deploy.set_defaults(func=cmd_deploy)

    # restart
    p_restart = subparsers.add_parser("restart", help="Restart container Docker aplikasi di host")
    p_restart.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi")
    p_restart.set_defaults(func=cmd_restart)

    # logs
    p_logs = subparsers.add_parser("logs", help="Lihat log runtime container atau antrean build")
    p_logs.add_argument("--app", required=True, help="Nama, ID, atau UUID aplikasi")
    p_logs.add_argument("--tail", type=int, default=100, help="Jumlah baris log terakhir (default: 100)")
    p_logs.add_argument("--deployment", action="store_true", help="Lihat log antrean build Coolify")
    p_logs.set_defaults(func=cmd_logs)

    # sync-aina-wa
    p_sync = subparsers.add_parser("sync-aina-wa", help="Setel otomatis provider WhatsApp Aina ke aplikasi")
    p_sync.add_argument("--app", default="sipedas", help="Aplikasi target (default: sipedas)")
    p_sync.add_argument("--base-url", help="Base URL Whatsmeow")
    p_sync.add_argument("--api-key", help="API Key Whatsmeow")
    p_sync.add_argument("--redeploy", action="store_true", help="Trigger redeploy setelah sinkronisasi")
    p_sync.add_argument("--force-rebuild", action="store_true", help="Paksa rebuild image saat redeploy")
    p_sync.set_defaults(func=cmd_sync_aina_wa)

    # deployments
    p_deps = subparsers.add_parser("deployments", help="Lihat riwayat antrean deployment Coolify")
    p_deps.add_argument("--app", help="Filter berdasarkan aplikasi tertentu")
    p_deps.add_argument("--limit", type=int, default=10, help="Batas jumlah deployment (default: 10)")
    p_deps.set_defaults(func=cmd_deployments)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
