from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crewai_enterprise_pipeline_api.db.base import Base, TimestampedMixin


class CaseRecord(TimestampedMixin, Base):
    __tablename__ = "cases"

    name: Mapped[str] = mapped_column(String(255))
    target_name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100), default="India")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    motion_pack: Mapped[str] = mapped_column(String(80))
    sector_pack: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="draft")

    documents: Mapped[list[DocumentArtifactRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="DocumentArtifactRecord.created_at",
        lazy="selectin",
    )
    evidence_items: Mapped[list[EvidenceNodeRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="EvidenceNodeRecord.created_at",
        lazy="selectin",
    )
    request_items: Mapped[list[RequestItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="RequestItemRecord.created_at",
        lazy="selectin",
    )
    qa_items: Mapped[list[QaItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="QaItemRecord.created_at",
        lazy="selectin",
    )


class DocumentArtifactRecord(TimestampedMixin, Base):
    __tablename__ = "document_artifacts"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(80))
    document_kind: Mapped[str] = mapped_column(String(120))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="received")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sha256_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="documents")


class EvidenceNodeRecord(TimestampedMixin, Base):
    __tablename__ = "evidence_nodes"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    evidence_kind: Mapped[str] = mapped_column(String(60))
    workstream_domain: Mapped[str] = mapped_column(String(80))
    citation: Mapped[str] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(default=0.7)

    case: Mapped[CaseRecord] = relationship(back_populates="evidence_items")


class RequestItemRecord(TimestampedMixin, Base):
    __tablename__ = "request_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="request_items")


class QaItemRecord(TimestampedMixin, Base):
    __tablename__ = "qa_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open")

    case: Mapped[CaseRecord] = relationship(back_populates="qa_items")
