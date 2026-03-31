from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    type_annotation_map: dict[Any, Any] = {datetime: DateTime(timezone=True)}


class TimestampedMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class TenantScopedMixin:
    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
