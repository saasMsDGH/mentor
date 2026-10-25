#!/usr/bin/env python3
"""Run PostgreSQL integration tests in a disposable, network-disabled container.

Only the unique container created here is stopped. No ports are published;
clients connect over a private temporary Unix socket. Passwords are generated
per run, passed through the environment and never printed or committed.
"""

import argparse
import base64
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "pgvector/pgvector@sha256:2ba9ca5f2e7daa0f0e7723cba1ee9167bab54efd3640516a44ac1a928dd67e7a"
DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]


def docker(*args, **kwargs):
    return subprocess.run([*DOCKER, *args], check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        command = [sys.executable, "-m", "pytest", "tests/integration/test_postgres_runtime.py", "tests/test_mentor_learning_journey.py", "-q", "-o", "addopts=", "--timeout=60"]

    # Refuse an implicit remote daemon; mounted socket paths must be local.
    docker("info", "--format", "{{.ServerVersion}}", stdout=subprocess.DEVNULL)
    name = "mentor-pg-test-" + secrets.token_hex(6)
    admin_password = secrets.token_hex(24)
    migration_password = secrets.token_hex(24)
    runtime_password = secrets.token_hex(24)
    docker_env = {**os.environ, "POSTGRES_PASSWORD": admin_password, "PGPASSWORD": admin_password}
    started = False
    with tempfile.TemporaryDirectory(prefix="mentor-pg-", dir="/tmp") as directory:
        work = Path(directory)
        socket_dir = work / "socket"
        socket_dir.mkdir(mode=0o755)
        try:
            docker("run", "--detach", "--rm", "--pull=never", "--name", name,
                   "--label", "mentor.disposable-test=true", "--network", "none",
                   "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
                   "--tmpfs", "/var/lib/postgresql:rw,size=384m",
                   "--mount", f"type=bind,source={socket_dir},target=/var/run/postgresql",
                   "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_DB=mentor_test",
                   "--env", "POSTGRES_INITDB_ARGS=--auth-local=scram-sha-256 --auth-host=scram-sha-256",
                   IMAGE, "postgres", "-c", "listen_addresses=", env=docker_env,
                   stdout=subprocess.DEVNULL)
            started = True
            for _ in range(60):
                process = subprocess.run([*DOCKER, "exec", name, "cat", "/proc/1/comm"],
                                         text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                status = subprocess.run([*DOCKER, "exec", "--env", "PGPASSWORD", name,
                                         "psql", "-X", "-q", "-U", "postgres", "-d", "mentor_test", "-c", "SELECT 1"],
                                        env=docker_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if process.stdout.strip() == "postgres" and status.returncode == 0 and (socket_dir / ".s.PGSQL.5432").exists():
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Disposable PostgreSQL did not become ready over its Unix socket")
            sql = f"""
CREATE ROLE mentor_migrate LOGIN PASSWORD '{migration_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE mentor_runtime LOGIN PASSWORD '{runtime_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER DATABASE mentor_test OWNER TO mentor_migrate;
CREATE EXTENSION vector;
GRANT CONNECT ON DATABASE mentor_test TO mentor_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE mentor_migrate IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mentor_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE mentor_migrate IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO mentor_runtime;
"""
            try:
                docker("exec", "--interactive", "--env", "PGPASSWORD", name, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "mentor_test",
                       input=sql, env=docker_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc:
                message = exc.stderr or "PostgreSQL test setup failed"
                for password in (admin_password, migration_password, runtime_password):
                    message = message.replace(password, "[redacted]")
                raise RuntimeError(message) from None
            environment = {**os.environ,
                           "ENVIRONMENT": "development", "APP_AUTO_CREATE_TABLES": "false",
                           "DATABASE_URL": "sqlite+aiosqlite:////tmp/mentor-pg-controller.db"}
            for role, password, variable in [("mentor_migrate", migration_password, "MENTOR_POSTGRES_TEST_DSN_FILE"),
                                              ("mentor_runtime", runtime_password, "MENTOR_POSTGRES_APP_DSN_FILE")]:
                path = work / f"{role}.dsn"
                path.write_text(f"postgresql+asyncpg://{role}:{password}@/mentor_test?host={quote(str(socket_dir), safe='')}")
                path.chmod(0o600)
                environment[variable] = str(path)
            print("PostgreSQL integration: local disposable container; network disabled; no published ports", flush=True)
            result = subprocess.run(command, cwd=ROOT, env=environment)
            if result.returncode == 0 and not args.command:
                api_image = os.environ.get("MENTOR_API_TEST_IMAGE")
                if api_image:
                    # Exercise the exact Kubernetes migration command in the
                    # production image with only its DDL account, no JWT or
                    # encryption key and no application create_all().
                    migration_environment = {**os.environ, "DATABASE_URL":
                        f"postgresql+asyncpg://mentor_migrate:{migration_password}@/mentor_test?host=%2Fvar%2Frun%2Fpostgresql"}
                    docker("run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                           "--security-opt", "no-new-privileges", "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
                           "--tmpfs", "/tmp:rw,size=32m",
                           "--mount", f"type=bind,source={socket_dir},target=/var/run/postgresql,readonly",
                           "--env", "DATABASE_URL", api_image,
                           "alembic", "-c", "alembic-postgres.ini", "upgrade", "head",
                           env=migration_environment)
                    print("Production migration command verified with DDL credentials only", flush=True)
                    api_name = name + "-api"
                    api_environment = {**os.environ,
                                       "DATABASE_URL": f"postgresql+asyncpg://mentor_runtime:{runtime_password}@/mentor_test?host=%2Fvar%2Frun%2Fpostgresql",
                                       "JWT_SECRET_KEY": secrets.token_hex(32),
                                       "ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}
                    api_started = False
                    web_started = False
                    network_started = False
                    web_name = name + "-web"
                    network_name = name + "-internal"
                    try:
                        web_image = os.environ.get("MENTOR_WEB_TEST_IMAGE")
                        api_network_options = ["--network", "none"]
                        if web_image:
                            docker("network", "create", "--internal", "--label", "mentor.disposable-test=true", network_name,
                                   stdout=subprocess.DEVNULL)
                            network_started = True
                            api_network_options = ["--network", network_name, "--network-alias", "mentor-api"]
                        docker("run", "--detach", "--rm", "--name", api_name,
                               *api_network_options, "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                               "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
                               "--tmpfs", "/tmp:rw,size=32m", "--tmpfs", "/app/uploads:rw,uid=10001,gid=10001,size=32m",
                               "--mount", f"type=bind,source={socket_dir},target=/var/run/postgresql,readonly",
                               "--env", "DATABASE_URL", "--env", "JWT_SECRET_KEY", "--env", "ENCRYPTION_KEY",
                               "--env", "LLM_PROVIDER=custom", "--env", "CUSTOM_LLM_BASE_URL=http://127.0.0.1:9/v1",
                               "--env", "CUSTOM_LLM_MODEL=qualification-unconfigured", api_image,
                               env=api_environment, stdout=subprocess.DEVNULL)
                        api_started = True
                        check = (ROOT / "scripts" / "check_api_image.py").read_text()
                        docker("exec", api_name, "python", "-c", check)
                        if web_image:
                            docker("run", "--detach", "--rm", "--name", web_name,
                                   "--network", network_name, "--read-only", "--cap-drop", "ALL",
                                   "--security-opt", "no-new-privileges", "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
                                   "--tmpfs", "/tmp:rw,size=32m",
                                   "--tmpfs", "/app/apps/web/.next/cache:rw,uid=1001,gid=1001,size=64m",
                                   web_image, stdout=subprocess.DEVNULL)
                            web_started = True
                            docker("exec", web_name, "node", "--input-type=module", "-e", (ROOT / "scripts/check_web_image.mjs").read_text())
                    except subprocess.CalledProcessError:
                        if api_started:
                            logs = subprocess.run([*DOCKER, "logs", "--tail", "20", api_name], text=True, capture_output=True)
                            diagnostic = logs.stdout + logs.stderr
                            for value in (admin_password, migration_password, runtime_password,
                                          api_environment["JWT_SECRET_KEY"], api_environment["ENCRYPTION_KEY"]):
                                diagnostic = diagnostic.replace(value, "[redacted]")
                            print(diagnostic, file=sys.stderr)
                        raise
                    finally:
                        if web_started:
                            docker("stop", "--time", "10", web_name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if api_started:
                            docker("stop", "--time", "10", api_name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if network_started:
                            docker("network", "rm", network_name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                def psql(database, sql):
                    return docker("exec", "--interactive", "--env", "PGPASSWORD", name,
                                  "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database,
                                  input=sql, env=docker_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

                psql("postgres", "CREATE DATABASE mentor_restore OWNER mentor_migrate;")
                docker("exec", "--env", "PGPASSWORD", name, "pg_dump", "-U", "postgres", "-d", "mentor_test",
                       "--format=custom", "--file=/tmp/mentor-backup.dump", env=docker_env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                docker("exec", "--env", "PGPASSWORD", name, "pg_restore", "-U", "postgres", "-d", "mentor_restore",
                       "--exit-on-error", "/tmp/mentor-backup.dump", env=docker_env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                tables = psql("mentor_test", "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
                if int(psql("mentor_test", "SELECT count(*) FROM practice_results")) < 1:
                    raise RuntimeError("Backup verification requires persisted learning attempts")
                for table in tables:
                    if not re.fullmatch(r"[a-z_][a-z_0-9]*", table):
                        raise RuntimeError("Unexpected test table name")
                    fingerprint = (
                        'SELECT count(*), md5(coalesce(string_agg(row_to_json(r)::text, '
                        f"""E'\\n' ORDER BY row_to_json(r)::text), '')) FROM "{table}" r"""
                    )
                    if psql("mentor_test", fingerprint) != psql("mentor_restore", fingerprint):
                        raise RuntimeError("Restored application data differs from the isolated source database")
                print(f"Backup/restore verified: {len(tables)} tables, including persisted learning attempts", flush=True)
            return result.returncode
        finally:
            if started:
                # The image owns its socket directory. Return the temporary
                # bind mount to the invoking user before local cleanup.
                try:
                    docker("exec", "--user", "0", name, "chown", f"{os.getuid()}:{os.getgid()}", "/var/run/postgresql",
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                finally:
                    docker("stop", "--time", "10", name, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())
