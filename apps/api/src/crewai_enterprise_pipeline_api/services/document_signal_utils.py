from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ArtifactTextSnapshot:
    artifact_id: str | None
    title: str
    document_kind: str
    source_kind: str
    original_filename: str | None
    workstream_domains: set[str] = field(default_factory=set)
    evidence_ids: list[str] = field(default_factory=list)
    text: str = ""


def collect_artifact_snapshots(case) -> list[ArtifactTextSnapshot]:
    snapshots_by_artifact: dict[str | None, ArtifactTextSnapshot] = {}
    evidence_by_artifact: dict[str | None, list[Any]] = {}
    for evidence in case.evidence_items:
        evidence_by_artifact.setdefault(getattr(evidence, "artifact_id", None), []).append(
            evidence
        )

    for document in case.documents:
        chunk_text = "\n\n".join(chunk.text for chunk in getattr(document, "chunks", []))
        linked_evidence = evidence_by_artifact.get(document.id, [])
        evidence_text = "\n".join(
            "\n".join(
                filter(
                    None,
                    [
                        getattr(item, "title", None),
                        getattr(item, "citation", None),
                        getattr(item, "excerpt", None),
                    ],
                )
            )
            for item in linked_evidence
        )
        snapshot = ArtifactTextSnapshot(
            artifact_id=document.id,
            title=document.title,
            document_kind=document.document_kind,
            source_kind=document.source_kind,
            original_filename=document.original_filename,
            workstream_domains={
                getattr(item, "workstream_domain", "")
                for item in linked_evidence
                if getattr(item, "workstream_domain", "")
            },
            evidence_ids=[item.id for item in linked_evidence],
            text="\n\n".join(filter(None, [chunk_text, evidence_text])),
        )
        snapshots_by_artifact[document.id] = snapshot

    orphan_evidence = evidence_by_artifact.get(None, [])
    if orphan_evidence:
        snapshots_by_artifact[None] = ArtifactTextSnapshot(
            artifact_id=None,
            title="Detached evidence bundle",
            document_kind="detached_evidence",
            source_kind="derived",
            original_filename=None,
            workstream_domains={
                getattr(item, "workstream_domain", "")
                for item in orphan_evidence
                if getattr(item, "workstream_domain", "")
            },
            evidence_ids=[item.id for item in orphan_evidence],
            text="\n\n".join(
                "\n".join(
                    filter(
                        None,
                        [
                            getattr(item, "title", None),
                            getattr(item, "citation", None),
                            getattr(item, "excerpt", None),
                        ],
                    )
                )
                for item in orphan_evidence
            ),
        )

    return [snapshot for snapshot in snapshots_by_artifact.values() if snapshot.text.strip()]


def score_snapshot_relevance(
    snapshot: ArtifactTextSnapshot,
    *,
    workstream_domains: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    document_kind_keywords: tuple[str, ...] = (),
) -> int:
    score = 0
    text = " ".join(
        filter(
            None,
            [
                snapshot.title,
                snapshot.document_kind,
                snapshot.original_filename,
                snapshot.text,
            ],
        )
    ).lower()

    if workstream_domains and snapshot.workstream_domains.intersection(workstream_domains):
        score += 5
    for keyword in keywords:
        if keyword.lower() in text:
            score += 2
    for keyword in document_kind_keywords:
        if keyword.lower() in snapshot.document_kind.lower():
            score += 3
    return score
