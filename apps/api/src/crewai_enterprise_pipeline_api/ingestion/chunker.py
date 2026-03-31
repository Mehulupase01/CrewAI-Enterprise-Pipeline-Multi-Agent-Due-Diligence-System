"""Semantic chunking engine.

Splits text by section headings > paragraphs > sentences, producing
chunks that carry section context, character offsets, and optional
page numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(
    r"^(?:#{1,4}\s+.+|[A-Z][A-Z0-9]{1,}(?:[ /&,\-][A-Z][A-Z0-9]*){1,})\s*$",
    re.MULTILINE,
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_PAGE_MARKER_RE = re.compile(r"^\[Page (\d+)\]", re.MULTILINE)


@dataclass
class SemanticChunk:
    chunk_index: int
    section_title: str | None
    text: str
    page_number: int | None
    char_start: int
    char_end: int


def semantic_chunk(
    text: str,
    *,
    max_chars: int = 1200,
) -> list[SemanticChunk]:
    """Split *text* into semantically aware chunks.

    Strategy:
      1. Split by section headings (markdown ``#`` or ALL-CAPS lines).
      2. Within each section, split by paragraphs (double newline).
      3. If a paragraph exceeds *max_chars*, split by sentence boundaries.
      4. Each chunk carries ``section_title``, ``char_start``, ``char_end``,
         and the nearest preceding ``[Page N]`` marker (if present).
    """
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not cleaned:
        return []

    sections = _split_sections(cleaned)
    chunks: list[SemanticChunk] = []
    chunk_index = 0

    for section_title, section_text, section_offset in sections:
        paragraphs = _split_paragraphs(section_text, section_offset)
        buffer = ""
        buffer_start = -1

        for para_text, para_offset in paragraphs:
            candidate = f"{buffer}\n\n{para_text}".strip() if buffer else para_text
            cand_start = buffer_start if buffer else para_offset

            if len(candidate) <= max_chars:
                buffer = candidate
                buffer_start = cand_start
                continue

            if buffer:
                page = _detect_page(cleaned, buffer_start)
                chunks.append(
                    SemanticChunk(
                        chunk_index=chunk_index,
                        section_title=section_title,
                        text=buffer,
                        page_number=page,
                        char_start=buffer_start,
                        char_end=buffer_start + len(buffer),
                    )
                )
                chunk_index += 1

            if len(para_text) <= max_chars:
                buffer = para_text
                buffer_start = para_offset
            else:
                for sub_text, sub_offset in _split_sentences(para_text, para_offset, max_chars):
                    page = _detect_page(cleaned, sub_offset)
                    chunks.append(
                        SemanticChunk(
                            chunk_index=chunk_index,
                            section_title=section_title,
                            text=sub_text,
                            page_number=page,
                            char_start=sub_offset,
                            char_end=sub_offset + len(sub_text),
                        )
                    )
                    chunk_index += 1
                buffer = ""
                buffer_start = -1

        if buffer:
            page = _detect_page(cleaned, buffer_start)
            chunks.append(
                SemanticChunk(
                    chunk_index=chunk_index,
                    section_title=section_title,
                    text=buffer,
                    page_number=page,
                    char_start=buffer_start,
                    char_end=buffer_start + len(buffer),
                )
            )
            chunk_index += 1

    return chunks


def _split_sections(
    text: str,
) -> list[tuple[str | None, str, int]]:
    """Return ``(title, body_text, char_offset)`` tuples."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [(None, text, 0)]

    sections: list[tuple[str | None, str, int]] = []

    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble, 0))

    for i, match in enumerate(matches):
        title = match.group().strip().lstrip("#").strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((title, body, body_start))

    return sections


def _split_paragraphs(
    text: str,
    base_offset: int,
) -> list[tuple[str, int]]:
    """Split text on double-newlines, returning ``(para, absolute_offset)``."""
    parts = re.split(r"\n\n+", text)
    result: list[tuple[str, int]] = []
    pos = 0
    for part in parts:
        stripped = part.strip()
        if stripped:
            idx = text.index(part, pos)
            result.append((stripped, base_offset + idx))
            pos = idx + len(part)
    return result


def _split_sentences(
    text: str,
    base_offset: int,
    max_chars: int,
) -> list[tuple[str, int]]:
    """Split a long paragraph by sentence boundaries into <=max_chars pieces."""
    sentences = _SENTENCE_RE.split(text)
    result: list[tuple[str, int]] = []
    buffer = ""
    buf_offset = base_offset
    pos = 0

    for sentence in sentences:
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= max_chars:
            if not buffer:
                buf_offset = base_offset + pos
            buffer = candidate
        else:
            if buffer:
                result.append((buffer, buf_offset))
            buffer = sentence
            buf_offset = base_offset + pos
            if len(buffer) > max_chars:
                start = 0
                while start < len(buffer):
                    end = start + max_chars
                    result.append((buffer[start:end], buf_offset + start))
                    start = end
                buffer = ""
        pos = text.index(sentence, pos) + len(sentence) if sentence in text[pos:] else pos

    if buffer:
        result.append((buffer, buf_offset))

    return result


def _detect_page(full_text: str, offset: int) -> int | None:
    """Find the nearest ``[Page N]`` marker at or before *offset*."""
    best: int | None = None
    for match in _PAGE_MARKER_RE.finditer(full_text):
        if match.start() <= offset:
            best = int(match.group(1))
        else:
            break
    return best
