"""Compilation-only PostgreSQL type checks; no live database is implied."""

import uuid

import pytest
from sqlalchemy.dialects import postgresql, sqlite
from pydantic import ValidationError

from config import Settings
from models.compat import CompatUUID, CompatVector
from models.content import CourseContentTree
from models.user import User


def test_database_url_requires_async_postgres_driver():
    settings = Settings(_env_file=None, database_url="postgresql+asyncpg://localhost/mentor")
    assert settings.database_url.startswith("postgresql+asyncpg://")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql://localhost/mentor")


def test_uuid_dialect_and_sqlite_roundtrip():
    dialect_pg = postgresql.dialect()
    dialect_sqlite = sqlite.dialect()
    assert "UUID" in User.__table__.c.id.type.compile(dialect=dialect_pg).upper()
    assert "VARCHAR" in User.__table__.c.id.type.compile(dialect=dialect_sqlite).upper()

    value = uuid.uuid4()
    typ = CompatUUID()
    assert typ.process_bind_param(value, dialect_sqlite) == str(value)
    assert typ.process_result_value(str(value), dialect_sqlite) == value
    assert typ.process_bind_param(str(value), dialect_pg) == value
    assert typ.process_result_value(value, dialect_pg) == value


def test_sqlite_vectors_still_roundtrip_as_json():
    typ = CompatVector(3)
    value = [0.1, 0.2, 0.3]
    serialized = typ.process_bind_param(value, sqlite.dialect())
    assert isinstance(serialized, str)
    assert typ.process_result_value(serialized, sqlite.dialect()) == value


def test_native_postgres_types_compile_when_pgvector_is_installed():
    pytest.importorskip("pgvector")
    dialect_pg = postgresql.dialect()
    columns = CourseContentTree.__table__.c
    assert columns.blocks_json.type.compile(dialect=dialect_pg) == "JSONB"
    assert columns.search_vector.type.compile(dialect=dialect_pg) == "TSVECTOR"
    assert "VECTOR(1536)" in columns.embedding.type.compile(dialect=dialect_pg).upper()
    typ = CompatVector(3)
    assert typ.process_bind_param([0.1, 0.2, 0.3], dialect_pg) == [0.1, 0.2, 0.3]


def test_all_model_tables_and_indexes_compile_for_postgresql():
    from database import Base
    from sqlalchemy.schema import CreateIndex, CreateTable

    pytest.importorskip("pgvector")
    dialect = postgresql.dialect()
    tables = Base.metadata.sorted_tables
    assert len(tables) > 20, "All application models must be registered"
    for table in tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in ddl
        for index in table.indexes:
            assert "CREATE" in str(CreateIndex(index).compile(dialect=dialect))


def test_postgres_native_vector_processors_roundtrip():
    pytest.importorskip("pgvector")
    dialect = postgresql.dialect()
    typ = CompatVector(3).dialect_impl(dialect)
    bind = typ.bind_processor(dialect)
    result = typ.result_processor(dialect, None)
    assert result(bind([0.1, 0.2, 0.3])) == pytest.approx([0.1, 0.2, 0.3])
    with pytest.raises(ValueError, match="dimensions"):
        bind([1.0, 2.0])


@pytest.mark.parametrize("value", [[float("nan"), 0, 1], [float("inf"), 0, 1], [[1], 2, 3], 7])
def test_postgres_rejects_invalid_embedding_values(value):
    with pytest.raises(ValueError):
        CompatVector(3).process_bind_param(value, postgresql.dialect())
