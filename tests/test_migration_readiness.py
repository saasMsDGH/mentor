"""Migration gates shared by PostgreSQL qualification and readiness probes."""

import io
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from alembic import command

from database import Base
from services.migrations import build_alembic_config, get_expected_migration_heads, summarize_migration_state


def test_postgres_baseline_is_renderable_without_a_database():
    config = build_alembic_config("postgresql")
    config.attributes["database_url"] = "postgresql+asyncpg://localhost/mentor?host=%2Ftmp%2Fmentor-pg-offline"
    config.output_buffer = io.StringIO()
    command.upgrade(config, "head", sql=True)
    sql = config.output_buffer.getvalue()
    assert sql.count("CREATE TABLE ") == len(Base.metadata.tables) + 1
    assert "VECTOR(1536)" in sql
    assert "CREATE TABLE users" in sql
    assert "mentor_pg_0001" in sql
    assert get_expected_migration_heads("postgresql") == ["mentor_pg_0001"]


def test_current_revision_with_missing_tables_is_not_ready():
    state = summarize_migration_state(
        table_names={"users", "alembic_version"}, current_heads=["head"], expected_heads=["head"],
        required_tables={"users", "courses"},
    )
    assert state.migration_status == "schema_incomplete"
    assert state.schema_ready is False


@pytest.mark.asyncio
async def test_postgres_startup_refuses_create_all(monkeypatch):
    from services import app_lifecycle
    monkeypatch.setattr(app_lifecycle.settings, "app_auto_create_tables", True)
    monkeypatch.setattr(app_lifecycle, "engine", SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    with pytest.raises(RuntimeError, match="explicit migrations"):
        await app_lifecycle._maybe_create_tables()


@pytest.mark.asyncio
async def test_readiness_reports_database_failure_without_raising(monkeypatch):
    from services import health
    from sqlalchemy.exc import OperationalError
    monkeypatch.setattr(health.database_module, "async_session", Mock(side_effect=OperationalError("SELECT 1", {}, RuntimeError("offline"))))
    monkeypatch.setattr(health, "get_llm_runtime_status", AsyncMock(return_value={"status": "ready"}))
    result = await health.get_readiness()
    assert result["ready"] is False
    assert result["database"] == "unreachable"


def test_postgres_migration_cli_needs_no_application_signing_keys():
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"JWT_SECRET_KEY", "ENCRYPTION_KEY"}}
    environment.update(ENVIRONMENT="production", AUTH_ENABLED="true", DATABASE_URL="postgresql+asyncpg://localhost/mentor")
    result = subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic-postgres.ini", "upgrade", "head", "--sql"],
                            cwd=Path(__file__).resolve().parents[1] / "apps/api", env=environment,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE users" in result.stdout
