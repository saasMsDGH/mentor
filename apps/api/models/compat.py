"""Cross-dialect SQLAlchemy types for the MENTOR migration.

SQLite values stay compatible with existing OpenTutor rows. PostgreSQL uses
native UUID/JSONB/TSVECTOR and pgvector (when explicitly installed).

IMPORTANT: These types do not constitute a completed PostgreSQL migration;
the initial schema, migrations, extension, indexes and search queries must
be validated against a real PostgreSQL instance separately.
"""

import json as _json
import math as _math
import uuid as _uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.types import TypeDecorator


class CompatUUID(TypeDecorator):
    """UUID objects in Python; UUID on PostgreSQL and char(36) on SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, _uuid.UUID) else _uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, _uuid.UUID) else _uuid.UUID(str(value))


CompatJSONB = JSON().with_variant(JSONB(), "postgresql")
CompatTSVECTOR = Text().with_variant(TSVECTOR(), "postgresql")


class _VectorType(TypeDecorator):
    """SQLite JSON text, or pgvector VECTOR(n) with list-valued Python API."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536):
        super().__init__()
        if dim <= 0:
            raise ValueError("Vector dimension must be positive")
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL vector columns require the pgvector Python package"
                ) from exc
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            # Native pgvector bindings must receive numeric values, not JSON text.
            values = _json.loads(value) if isinstance(value, str) else value
            try:
                if len(values) != self.dim:
                    raise ValueError(f"Expected {self.dim} vector dimensions")
                values = [float(item) for item in values]
            except (TypeError, OverflowError) as exc:
                raise ValueError("Vector must be a flat numeric sequence") from exc
            if not all(_math.isfinite(item) for item in values):
                raise ValueError("Vector values must be finite")
            return values
        return value if isinstance(value, str) else _json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, list):
            return value
        return _json.loads(value) if isinstance(value, str) else list(value)


class _TextVectorFactory:
    """Preserve CompatVector(1536) for existing OpenTutor models."""

    def __call__(self, dim: int = 1536):
        return _VectorType(dim)


CompatVector = _TextVectorFactory()
