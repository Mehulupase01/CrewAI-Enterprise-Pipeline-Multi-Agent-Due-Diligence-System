from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from crewai_enterprise_pipeline_api.domain.models import ReportTemplateKind

TEMPLATE_NAME_MAP = {
    ReportTemplateKind.STANDARD: "standard.md.j2",
    ReportTemplateKind.LENDER: "lender.md.j2",
    ReportTemplateKind.BOARD_MEMO: "board_memo.md.j2",
    ReportTemplateKind.ONE_PAGER: "one_pager.md.j2",
}


class ReportRendererService:
    def __init__(self) -> None:
        templates_dir = Path(__file__).resolve().parents[1] / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        self.environment.filters["money"] = self._money
        self.environment.filters["pct"] = self._pct
        self.environment.filters["safe_text"] = self._safe_text
        self.environment.filters["heading_label"] = self._heading_label

    def render_full_report(
        self,
        template_kind: ReportTemplateKind,
        context: dict[str, Any],
    ) -> str:
        template = self.environment.get_template(TEMPLATE_NAME_MAP[template_kind])
        return template.render(**context).strip() + "\n"

    def render_financial_annex(self, context: dict[str, Any]) -> str:
        template = self.environment.get_template("financial_annex.md.j2")
        return template.render(**context).strip() + "\n"

    @staticmethod
    def template_label(template_kind: ReportTemplateKind) -> str:
        labels = {
            ReportTemplateKind.STANDARD: "Standard Due Diligence Report",
            ReportTemplateKind.LENDER: "Lender Credit Report",
            ReportTemplateKind.BOARD_MEMO: "Board Memo",
            ReportTemplateKind.ONE_PAGER: "One-Pager",
        }
        return labels[template_kind]

    @staticmethod
    def _money(value: float | int | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:,.2f}"

    @staticmethod
    def _pct(value: float | int | None) -> str:
        if value is None:
            return "n/a"
        numeric = float(value)
        if abs(numeric) <= 1:
            numeric *= 100
        return f"{numeric:.2f}%"

    @staticmethod
    def _safe_text(value: str | None, fallback: str = "n/a") -> str:
        if value is None or not str(value).strip():
            return fallback
        return str(value).strip()

    @staticmethod
    def _heading_label(value: str) -> str:
        return value.replace("_", " ").title()

    @staticmethod
    def build_cover_subtitle(context: dict[str, Any]) -> str:
        memo = context["memo"]
        generated_at: datetime = context["generated_at"]
        return (
            f"Target: {memo.target_name} | Motion Pack: {memo.motion_pack.value} | "
            f"Sector Pack: {memo.sector_pack.value} | Generated: {generated_at.isoformat()}"
        )
