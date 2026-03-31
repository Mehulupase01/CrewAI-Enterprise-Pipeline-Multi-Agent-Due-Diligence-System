from __future__ import annotations

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from crewai_enterprise_pipeline_api.services.report_markdown import (
    BulletListBlock,
    HeadingBlock,
    ParagraphBlock,
    TableBlock,
    collect_toc_headings,
    parse_markdown_blocks,
)


class PdfService:
    def render_report(
        self,
        *,
        title: str,
        subtitle: str,
        template_label: str,
        markdown: str,
    ) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
        )
        styles = self._build_styles()
        story = [
            Paragraph(escape(title), styles["cover_title"]),
            Spacer(1, 10),
            Paragraph(escape(template_label), styles["cover_label"]),
            Spacer(1, 8),
            Paragraph(escape(subtitle), styles["cover_subtitle"]),
            PageBreak(),
        ]

        blocks = parse_markdown_blocks(markdown)
        toc_headings = [heading for heading in collect_toc_headings(blocks) if heading != title]
        if toc_headings:
            story.append(Paragraph("Table of Contents", styles["heading_1"]))
            story.append(Spacer(1, 6))
            for heading in toc_headings:
                story.append(Paragraph(f"• {escape(heading)}", styles["bullet"]))
            story.append(PageBreak())

        for block in blocks:
            if isinstance(block, HeadingBlock):
                style_key = f"heading_{min(block.level, 3)}"
                story.append(Paragraph(escape(block.text), styles[style_key]))
                story.append(Spacer(1, 4))
            elif isinstance(block, ParagraphBlock):
                story.append(Paragraph(escape(block.text), styles["body"]))
                story.append(Spacer(1, 4))
            elif isinstance(block, BulletListBlock):
                for item in block.items:
                    story.append(Paragraph(f"• {escape(item)}", styles["bullet"]))
                story.append(Spacer(1, 4))
            elif isinstance(block, TableBlock):
                table_data = [block.headers, *block.rows]
                table = Table(table_data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E7F5")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#F8FAFC")],
                            ),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 6))

        document.build(story)
        return buffer.getvalue()

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        sample = getSampleStyleSheet()
        return {
            "cover_title": ParagraphStyle(
                "CoverTitle",
                parent=sample["Title"],
                fontName="Helvetica-Bold",
                fontSize=24,
                leading=28,
                textColor=colors.HexColor("#0F172A"),
                alignment=1,
            ),
            "cover_label": ParagraphStyle(
                "CoverLabel",
                parent=sample["Heading2"],
                fontName="Helvetica-Oblique",
                fontSize=12,
                leading=15,
                textColor=colors.HexColor("#1D4ED8"),
                alignment=1,
            ),
            "cover_subtitle": ParagraphStyle(
                "CoverSubtitle",
                parent=sample["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=13,
                alignment=1,
            ),
            "heading_1": ParagraphStyle(
                "Heading1",
                parent=sample["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=4,
            ),
            "heading_2": ParagraphStyle(
                "Heading2",
                parent=sample["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=13,
                textColor=colors.HexColor("#1E293B"),
                spaceAfter=4,
            ),
            "heading_3": ParagraphStyle(
                "Heading3",
                parent=sample["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=11,
                textColor=colors.HexColor("#334155"),
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=sample["BodyText"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
            ),
            "bullet": ParagraphStyle(
                "Bullet",
                parent=sample["BodyText"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=12,
                leftIndent=10,
            ),
        }
