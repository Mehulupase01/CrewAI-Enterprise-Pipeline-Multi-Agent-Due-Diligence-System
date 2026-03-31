from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HeadingBlock:
    level: int
    text: str


@dataclass(slots=True)
class ParagraphBlock:
    text: str


@dataclass(slots=True)
class BulletListBlock:
    items: list[str]


@dataclass(slots=True)
class TableBlock:
    headers: list[str]
    rows: list[list[str]]


MarkdownBlock = HeadingBlock | ParagraphBlock | BulletListBlock | TableBlock


def parse_markdown_blocks(markdown: str) -> list[MarkdownBlock]:
    lines = markdown.splitlines()
    blocks: list[MarkdownBlock] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx].rstrip()
        stripped = line.strip()
        if not stripped:
            idx += 1
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            blocks.append(HeadingBlock(level=max(1, level), text=stripped[level:].strip()))
            idx += 1
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while idx < len(lines):
                candidate = lines[idx].strip()
                if not candidate.startswith("- "):
                    break
                items.append(candidate[2:].strip())
                idx += 1
            blocks.append(BulletListBlock(items=items))
            continue

        if _looks_like_table_header(stripped, lines, idx):
            header_cells = _split_table_row(stripped)
            idx += 2
            rows: list[list[str]] = []
            while idx < len(lines):
                candidate = lines[idx].strip()
                if "|" not in candidate or candidate.startswith("#") or candidate.startswith("- "):
                    break
                cells = _split_table_row(candidate)
                if len(cells) == len(header_cells):
                    rows.append(cells)
                idx += 1
            blocks.append(TableBlock(headers=header_cells, rows=rows))
            continue

        paragraph_lines = [stripped]
        idx += 1
        while idx < len(lines):
            candidate = lines[idx].strip()
            if (
                not candidate
                or candidate.startswith("#")
                or candidate.startswith("- ")
                or _looks_like_table_header(candidate, lines, idx)
            ):
                break
            paragraph_lines.append(candidate)
            idx += 1
        blocks.append(ParagraphBlock(text=" ".join(paragraph_lines)))

    return blocks


def collect_toc_headings(blocks: list[MarkdownBlock]) -> list[str]:
    headings: list[str] = []
    for block in blocks:
        if isinstance(block, HeadingBlock) and block.level <= 3:
            headings.append(block.text)
    return headings


def _looks_like_table_header(line: str, lines: list[str], idx: int) -> bool:
    if "|" not in line or idx + 1 >= len(lines):
        return False
    separator = lines[idx + 1].strip().replace("|", "").replace("-", "").replace(":", "").strip()
    return separator == ""


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip("|").split("|")]
