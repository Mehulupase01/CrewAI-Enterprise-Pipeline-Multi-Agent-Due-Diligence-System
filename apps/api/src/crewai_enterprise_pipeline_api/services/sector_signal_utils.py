from __future__ import annotations

import re
from collections.abc import Iterable

from crewai_enterprise_pipeline_api.services.document_signal_utils import (
    collect_artifact_snapshots,
    score_snapshot_relevance,
)

AMOUNT_PATTERN = re.compile(
    r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>crore|cr|lakh|lac|million|mn|billion|bn)?",
    re.IGNORECASE,
)
PERCENT_PATTERN = re.compile(r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*%", re.IGNORECASE)
DAYS_PATTERN = re.compile(r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*days?", re.IGNORECASE)
MONTHS_PATTERN = re.compile(r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*months?", re.IGNORECASE)

UNIT_MULTIPLIERS = {
    "crore": 10_000_000.0,
    "cr": 10_000_000.0,
    "lakh": 100_000.0,
    "lac": 100_000.0,
    "million": 1_000_000.0,
    "mn": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
}


def collect_sector_text(
    case,
    *,
    keywords: Iterable[str],
    workstream_domains: tuple[str, ...] = (),
    document_kind_keywords: tuple[str, ...] = (),
) -> str:
    snapshots = [
        snapshot
        for snapshot in collect_artifact_snapshots(case)
        if score_snapshot_relevance(
            snapshot,
            workstream_domains=workstream_domains,
            keywords=tuple(keywords),
            document_kind_keywords=document_kind_keywords,
        )
        > 0
    ]
    return "\n\n".join(
        filter(
            None,
            [
                "\n".join(
                    filter(
                        None,
                        [
                            snapshot.title,
                            snapshot.document_kind,
                            snapshot.original_filename,
                            snapshot.text,
                        ],
                    )
                )
                for snapshot in snapshots
            ],
        )
    )


def extract_amount(text: str, *keywords: str) -> float | None:
    if not text:
        return None
    for keyword in keywords:
        pattern = re.compile(
            rf"{re.escape(keyword)}[^0-9]{{0,40}}(?P<number>\d[\d,]*(?:\.\d+)?)"
            rf"\s*(?P<unit>crore|cr|lakh|lac|million|mn|billion|bn)?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return _normalize_amount(match.group("number"), match.group("unit"))
    return None


def extract_percentage(text: str, *keywords: str) -> float | None:
    if not text:
        return None
    for keyword in keywords:
        pattern = re.compile(
            rf"{re.escape(keyword)}[^0-9%]{{0,30}}(?P<number>\d[\d,]*(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return round(_normalize_number(match.group("number")) / 100.0, 6)
    return None


def extract_days(text: str, *keywords: str) -> float | None:
    if not text:
        return None
    for keyword in keywords:
        pattern = re.compile(
            rf"{re.escape(keyword)}[^0-9]{{0,25}}(?P<number>\d[\d,]*(?:\.\d+)?)\s*days?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return _normalize_number(match.group("number"))
    return None


def extract_months(text: str, *keywords: str) -> float | None:
    if not text:
        return None
    for keyword in keywords:
        pattern = re.compile(
            rf"{re.escape(keyword)}[^0-9]{{0,25}}(?P<number>\d[\d,]*(?:\.\d+)?)\s*months?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return _normalize_number(match.group("number"))
    return None


def extract_status_flag(
    text: str,
    *,
    anchor_keywords: tuple[str, ...],
    positive_markers: tuple[str, ...],
    negative_markers: tuple[str, ...],
) -> str | None:
    lowered = text.lower()
    for anchor in anchor_keywords:
        idx = lowered.find(anchor.lower())
        if idx < 0:
            continue
        window = lowered[idx : idx + 180]
        if any(marker in window for marker in negative_markers):
            return "negative"
        if any(marker in window for marker in positive_markers):
            return "positive"
    return None


def sentence_matches(text: str, *keywords: str, limit: int = 3) -> list[str]:
    if not text:
        return []
    fragments: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split())):
        lowered = sentence.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            fragments.append(sentence.strip())
        if len(fragments) >= limit:
            break
    return fragments


def _normalize_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _normalize_amount(raw: str, unit: str | None) -> float:
    value = _normalize_number(raw)
    if not unit:
        return value
    return value * UNIT_MULTIPLIERS.get(unit.lower(), 1.0)
