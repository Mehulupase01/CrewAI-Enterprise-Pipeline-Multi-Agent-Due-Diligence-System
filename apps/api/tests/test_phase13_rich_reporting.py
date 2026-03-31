from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from zipfile import ZipFile

from docx import Document

from crewai_enterprise_pipeline_api.evaluation.financial_fixtures import (
    build_financial_workbook_bytes,
)
from crewai_enterprise_pipeline_api.services.docx_service import DocxService
from crewai_enterprise_pipeline_api.services.pdf_service import PdfService


def _file_uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    return Path(unquote(parsed.path.lstrip("/")))


def _create_ready_case(client, *, motion_pack: str = "buy_side_diligence") -> str:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Phase13 Reporting",
            "target_name": "Phase13 Reporting Systems Private Limited",
            "summary": "Rich reporting validation case.",
            "motion_pack": motion_pack,
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert case_response.status_code == 201
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    for item in seed_response.json()["checklist_items"]:
        update_response = client.patch(
            f"/api/v1/cases/{case_id}/checklist/{item['id']}",
            json={
                "status": "satisfied",
                "owner": "Phase13 Reviewer",
                "note": "Satisfied for rich reporting validation.",
            },
        )
        assert update_response.status_code == 200

    workbook_bytes = build_financial_workbook_bytes()
    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "financial_workbook",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Financial workbook",
            "evidence_kind": "metric",
        },
        files={
            "file": (
                "financial_workbook.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload_response.status_code == 201

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Commercial summary",
            "evidence_kind": "metric",
            "workstream_domain": "commercial",
            "citation": "Commercial review pack FY26",
            "excerpt": (
                "Net revenue retention remained above 118 percent with no top-customer churn "
                "during the current period."
            ),
            "confidence": 0.92,
        },
    )
    assert evidence_response.status_code == 201

    approval_response = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "Phase13 Approver",
            "note": "Case is ready for rich reporting output generation.",
        },
    )
    assert approval_response.status_code == 201
    assert approval_response.json()["decision"] == "approved"
    return case_id


def test_full_report_endpoint_renders_all_templates(client) -> None:
    case_id = _create_ready_case(client)

    expected_titles = {
        "standard": "Full Executive Memo",
        "lender": "Lender Credit Report",
        "board_memo": "Board Memo",
        "one_pager": "Due Diligence One-Pager",
    }

    for template_kind, expected_title in expected_titles.items():
        response = client.get(
            f"/api/v1/cases/{case_id}/reports/full-report?report_template={template_kind}"
        )
        assert response.status_code == 200
        assert expected_title in response.text
        assert "Executive Summary" in response.text or "Credit View" in response.text


def test_financial_annex_endpoint_contains_period_and_ratio_sections(client) -> None:
    case_id = _create_ready_case(client)

    response = client.get(f"/api/v1/cases/{case_id}/reports/financial-annex")
    assert response.status_code == 200
    assert "# Financial Annex" in response.text
    assert "## Period Summary" in response.text
    assert "## Ratio Snapshot" in response.text
    assert "FY22" in response.text


def test_docx_service_generates_valid_docx_from_markdown() -> None:
    service = DocxService()
    docx_bytes = service.render_report(
        title="Board Memo",
        subtitle="Target: Example Co | Generated: 2026-03-31T17:00:00Z",
        template_label="Board Memo",
        markdown=(
            "# Board Memo\n\n"
            "## Executive Summary\n"
            "All key approvals are in place.\n\n"
            "## Key Risks\n"
            "- Customer concentration remains elevated.\n"
            "- GST demand is under response.\n"
        ),
    )
    document = Document(BytesIO(docx_bytes))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Board Memo" in text
    assert "Table of Contents" in text
    assert "Executive Summary" in text


def test_pdf_service_generates_valid_pdf_from_markdown() -> None:
    service = PdfService()
    pdf_bytes = service.render_report(
        title="Lender Credit Report",
        subtitle="Target: Example Co | Generated: 2026-03-31T17:00:00Z",
        template_label="Lender Credit Report",
        markdown=(
            "# Lender Credit Report\n\n"
            "## Credit View\n"
            "Overall leverage remains manageable.\n\n"
            "## Covenant Tracking\n"
            "| Covenant | Status |\n"
            "| --- | --- |\n"
            "| DSCR | compliant |\n"
        ),
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_workflow_run_and_export_package_include_rich_reporting_artifacts(client) -> None:
    case_id = _create_ready_case(client)

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={
            "requested_by": "Phase13 Operator",
            "note": "Generate a board-ready rich reporting package.",
            "report_template": "board_memo",
        },
    )
    assert run_response.status_code == 201
    run_payload = run_response.json()["run"]
    assert run_payload["report_template"] == "board_memo"

    detail_response = client.get(f"/api/v1/cases/{case_id}/runs/{run_payload['id']}")
    assert detail_response.status_code == 200
    run_detail = detail_response.json()
    bundle_kinds = {bundle["bundle_kind"] for bundle in run_detail["report_bundles"]}
    assert {
        "full_report_markdown",
        "financial_annex_markdown",
        "full_report_docx",
        "full_report_pdf",
    }.issubset(bundle_kinds)

    docx_bundle = next(
        bundle
        for bundle in run_detail["report_bundles"]
        if bundle["bundle_kind"] == "full_report_docx"
    )
    pdf_bundle = next(
        bundle
        for bundle in run_detail["report_bundles"]
        if bundle["bundle_kind"] == "full_report_pdf"
    )
    assert docx_bundle["storage_path"]
    assert docx_bundle["file_name"].endswith(".docx")
    assert docx_bundle["byte_size"] > 0
    assert pdf_bundle["storage_path"]
    assert pdf_bundle["file_name"].endswith(".pdf")
    assert pdf_bundle["byte_size"] > 0

    docx_download = client.get(
        f"/api/v1/cases/{case_id}/runs/{run_payload['id']}/report-bundles/{docx_bundle['id']}/download"
    )
    assert docx_download.status_code == 200
    assert docx_download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(docx_download.content) == docx_bundle["byte_size"]

    pdf_download = client.get(
        f"/api/v1/cases/{case_id}/runs/{run_payload['id']}/report-bundles/{pdf_bundle['id']}/download"
    )
    assert pdf_download.status_code == 200
    assert pdf_download.content.startswith(b"%PDF")

    export_response = client.post(
        f"/api/v1/cases/{case_id}/runs/{run_payload['id']}/export-package",
        json={
            "requested_by": "Phase13 Operator",
            "title": "Board Reporting Export",
            "include_json_snapshot": True,
        },
    )
    assert export_response.status_code == 201
    export_payload = export_response.json()
    assert "reports/full_report_board_memo.md" in export_payload["included_files"]
    assert "reports/full_report_board_memo.docx" in export_payload["included_files"]
    assert "reports/full_report_board_memo.pdf" in export_payload["included_files"]
    assert "reports/financial_annex.md" in export_payload["included_files"]

    archive_path = _file_uri_to_path(export_payload["storage_path"])
    assert archive_path.exists()
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert "reports/full_report_board_memo.md" in names
        assert "reports/full_report_board_memo.docx" in names
        assert "reports/full_report_board_memo.pdf" in names
        assert "reports/financial_annex.md" in names
