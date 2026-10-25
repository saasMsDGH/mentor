"""Real PostgreSQL lifecycle tests, run only through scripts/test_postgres.py.

The controller creates an empty, isolated database and a separate application
role without DDL privileges. No shared or deployed database is accepted here.
"""

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock

from database import Base
from services.migrations import (
    bootstrap_alembic_version_table,
    build_alembic_config,
    inspect_database_migrations,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    not os.environ.get("MENTOR_POSTGRES_TEST_DSN_FILE"),
    reason="Use scripts/test_postgres.py for an isolated real PostgreSQL database",
)]


def read_test_url(variable):
    value = Path(os.environ[variable]).read_text().strip()
    url = make_url(value)
    if url.database != "mentor_test" or url.host or not url.query.get("host", "").startswith("/tmp/mentor-pg-"):
        raise RuntimeError("Only the controller's private Unix socket database is allowed")
    return value


def migrate(url, direction, revision):
    config = build_alembic_config("postgresql")
    config.attributes["database_url"] = url
    getattr(command, direction)(config, revision)


async def test_postgresql_migration_lifecycle():
    url = read_test_url("MENTOR_POSTGRES_TEST_DSN_FILE")
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            state = await conn.run_sync(inspect_database_migrations)
            assert state.migration_status == "schema_missing"
            with pytest.raises(RuntimeError, match="never stamped"):
                await conn.run_sync(bootstrap_alembic_version_table)
        await asyncio.to_thread(migrate, url, "upgrade", "head")
        await asyncio.to_thread(migrate, url, "upgrade", "head")
        async with engine.connect() as conn:
            state = await conn.run_sync(inspect_database_migrations)
            assert state.schema_ready
            assert state.current_revisions == ["mentor_pg_0001"]
            assert state.expected_revisions == ["mentor_pg_0001"]
            tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
            assert set(Base.metadata.tables) <= tables
            differences = await conn.run_sync(lambda c: compare_metadata(
                MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata,
            ))
            assert differences == []
            for table in ("course_content_tree", "conversation_memories"):
                index = await conn.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename=:table"), {"table": table})
                assert index.fetchall()
        await asyncio.to_thread(migrate, url, "downgrade", "base")
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
            assert not (set(Base.metadata.tables) & tables)
            assert (await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))).scalar()
        await asyncio.to_thread(migrate, url, "upgrade", "head")
    finally:
        await engine.dispose()


async def test_native_pgvector_jsonb_and_fulltext_roundtrip():
    import uuid
    from sqlalchemy import Float, bindparam, select
    from models.content import CourseContentTree
    from models.course import Course
    from models.user import User
    from models.compat import CompatUUID

    engine = create_async_engine(read_test_url("MENTOR_POSTGRES_APP_DSN_FILE"), poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    course_id = uuid.uuid4()
    try:
        async with factory() as db:
            user = User(name="Native PostgreSQL test learner")
            db.add(user)
            await db.flush()
            db.add(Course(id=course_id, user_id=user.id, name="Native types"))
            await db.flush()
            first = CourseContentTree(course_id=course_id, title="Dichotomie", content="recherche dichotomique tableau trié",
                                      blocks_json={"verified": True}, embedding=[1.0] + [0.0] * 1535)
            second = CourseContentTree(course_id=course_id, title="Parcours", content="recherche linéaire",
                                       embedding=[0.0, 1.0] + [0.0] * 1534)
            db.add_all([first, second])
            await db.commit()
            distance = CourseContentTree.embedding.op("<=>", return_type=Float)(
                bindparam("query_embedding", type_=CourseContentTree.embedding.type))
            rows = (await db.execute(select(CourseContentTree, distance.label("distance"))
                                     .where(CourseContentTree.course_id == course_id)
                                     .order_by(distance).limit(2), {"query_embedding": [1.0] + [0.0] * 1535})).all()
            assert [row[0].id for row in rows] == [first.id, second.id]
            assert [row[1] for row in rows] == pytest.approx([0.0, 1.0])
            assert rows[0][0].blocks_json == {"verified": True}
            assert rows[0][0].embedding == [1.0] + [0.0] * 1535
            await db.execute(text("UPDATE course_content_tree SET search_vector=to_tsvector('simple', content) WHERE course_id=:course_id")
                             .bindparams(bindparam("course_id", type_=CompatUUID())), {"course_id": course_id})
            found = (await db.execute(text("SELECT title FROM course_content_tree WHERE course_id=:course_id AND search_vector @@ plainto_tsquery('simple', :query)")
                                     .bindparams(bindparam("course_id", type_=CompatUUID())), {"course_id": course_id, "query": "dichotomique"})).scalars().all()
            assert found == ["Dichotomie"]
            index_defs = (await db.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename='course_content_tree'"))).scalars().all()
            assert any("USING gin" in definition for definition in index_defs)
            assert any("USING hnsw" in definition for definition in index_defs)
            await db.commit()
    finally:
        await engine.dispose()


async def test_postgresql_runtime_is_dml_only_and_readiness_requires_migrations(monkeypatch):
    import database
    from main import app
    from httpx import ASGITransport, AsyncClient

    admin_url = read_test_url("MENTOR_POSTGRES_TEST_DSN_FILE")
    runtime_url = read_test_url("MENTOR_POSTGRES_APP_DSN_FILE")
    engine = create_async_engine(runtime_url, poolclass=NullPool)
    migration_engine = create_async_engine(admin_url, poolclass=NullPool)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "async_session", async_sessionmaker(engine, expire_on_commit=False))
    runtime = {"status": "ready", "primary_name": "test", "available_providers": ["test"],
               "provider_health": {"test": True}, "provider_details": {}, "llm_required": True}
    monkeypatch.setattr("services.health.get_llm_runtime_status", AsyncMock(return_value=runtime))
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user"))).scalar() is False
            assert (await conn.execute(text("SELECT has_schema_privilege(current_user,'public','CREATE')"))).scalar() is False
            assert (await conn.execute(text("SELECT has_table_privilege(current_user,'users','INSERT')"))).scalar() is True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://mentor.test") as client:
            ready = await client.get("/api/health/ready")
            assert ready.status_code == 200, ready.text
            health = await client.get("/api/health")
            assert health.json()["database_backend"] == "postgresql"
            assert health.json()["migration_status"] == "ready"
            async with migration_engine.begin() as conn:
                await conn.execute(text("UPDATE alembic_version SET version_num='outdated'"))
            try:
                outdated = await client.get("/api/health/ready")
                assert outdated.status_code == 503
                assert outdated.json()["schema"] == "out_of_date"
            finally:
                async with migration_engine.begin() as conn:
                    await conn.execute(text("UPDATE alembic_version SET version_num='mentor_pg_0001'"))
            async with migration_engine.begin() as conn:
                await conn.execute(text("ALTER TABLE notifications RENAME TO notifications_test_missing"))
            try:
                missing = await client.get("/api/health/ready")
                assert missing.status_code == 503
                assert missing.json()["schema"] == "schema_incomplete"
            finally:
                async with migration_engine.begin() as conn:
                    await conn.execute(text("ALTER TABLE notifications_test_missing RENAME TO notifications"))
            runtime["status"] = "degraded"
            assert (await client.get("/api/health/ready")).status_code == 503
    finally:
        await engine.dispose()
        await migration_engine.dispose()
