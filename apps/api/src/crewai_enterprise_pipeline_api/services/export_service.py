from __future__ import annotations

import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crewai_enterprise_pipeline_api.db.models import RunExportPackageRecord, WorkflowRunRecord
from crewai_enterprise_pipeline_api.domain.models import (
    RunExportPackageCreate,
    RunExportPackageKind,
    RunExportPackageSummary,
    WorkflowRunDetail,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.report_service = ReportService(session)
        self.storage_service = DocumentStorageService()

    async def create_run_export_package(
        self,
        case_id: str,
        run_id: str,
        payload: RunExportPackageCreate,
    ) -> RunExportPackageSummary | None:
        case_detail = await self.case_service.get_case(case_id)
        run_record = await self._get_run_record(case_id, run_id)
        if case_detail is None or run_record is None:
            return None

        run_detail = WorkflowRunDetail.model_validate(run_record)
        executive_memo = await self.report_service.build_executive_memo(case_id)
        if executive_memo is None:
            return None

        export_id = str(uuid4())
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        case_slug = self._slugify(case_detail.name)
        file_name = f"{case_slug}-{run_id}-export-{timestamp}.zip"
        title = payload.title or f"Run Export Package for {case_detail.name}"

        manifest = {
            "export_kind": RunExportPackageKind.RUN_REPORT_ARCHIVE.value,
            "generated_at": datetime.now(UTC).isoformat(),
            "requested_by": payload.requested_by,
            "case": case_detail.model_dump(mode="json"),
            "run": {
                "id": run_detail.id,
                "status": run_detail.status.value,
                "requested_by": run_detail.requested_by,
                "summary": run_detail.summary,
                "started_at": run_detail.started_at.isoformat()
                if run_detail.started_at is not None
                else None,
                "completed_at": run_detail.completed_at.isoformat()
                if run_detail.completed_at is not None
                else None,
            },
            "report_title": executive_memo.report_title,
            "report_status": executive_memo.report_status,
            "bundle_kinds": [bundle.bundle_kind.value for bundle in run_detail.report_bundles],
            "trace_event_count": len(run_detail.trace_events),
            "workstream_synthesis_count": len(run_detail.workstream_syntheses),
        }

        included_files: list[str] = []
        archive = io.BytesIO()
        with ZipFile(archive, mode="w", compression=ZIP_DEFLATED) as zip_file:
            readme = "\n".join(
                [
                    title,
                    "",
                    f"Case: {case_detail.name}",
                    f"Target: {case_detail.target_name}",
                    f"Run: {run_detail.id}",
                    f"Generated: {manifest['generated_at']}",
                    f"Requested by: {payload.requested_by}",
                ]
            )
            zip_file.writestr("README.txt", readme)
            included_files.append("README.txt")

            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
            included_files.append("manifest.json")

            for bundle in run_detail.report_bundles:
                bundle_path = self._bundle_path(bundle.bundle_kind.value)
                zip_file.writestr(bundle_path, bundle.content)
                included_files.append(bundle_path)

            zip_file.writestr(
                "data/run_trace.json",
                json.dumps(
                    [event.model_dump(mode="json") for event in run_detail.trace_events],
                    indent=2,
                ),
            )
            included_files.append("data/run_trace.json")

            zip_file.writestr(
                "data/workstream_syntheses.json",
                json.dumps(
                    [
                        synthesis.model_dump(mode="json")
                        for synthesis in run_detail.workstream_syntheses
                    ],
                    indent=2,
                ),
            )
            included_files.append("data/workstream_syntheses.json")

            if payload.include_json_snapshot:
                zip_file.writestr(
                    "data/case_snapshot.json",
                    json.dumps(case_detail.model_dump(mode="json"), indent=2),
                )
                included_files.append("data/case_snapshot.json")

        stored_artifact = self.storage_service.store_bytes(
            case_id=case_id,
            artifact_id=export_id,
            filename=file_name,
            content=archive.getvalue(),
        )

        record = RunExportPackageRecord(
            id=export_id,
            case_id=case_id,
            run_id=run_id,
            export_kind=RunExportPackageKind.RUN_REPORT_ARCHIVE.value,
            title=title,
            format="zip",
            file_name=file_name,
            summary=(
                f"Archive package for workflow run {run_id} with {len(included_files)} "
                "generated files."
            ),
            requested_by=payload.requested_by,
            storage_path=stored_artifact.storage_path,
            sha256_digest=stored_artifact.sha256_digest,
            byte_size=stored_artifact.byte_size,
            included_files=included_files,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return RunExportPackageSummary.model_validate(record)

    async def _get_run_record(self, case_id: str, run_id: str) -> WorkflowRunRecord | None:
        result = await self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.case_id == case_id, WorkflowRunRecord.id == run_id)
            .options(
                selectinload(WorkflowRunRecord.trace_events),
                selectinload(WorkflowRunRecord.report_bundles),
                selectinload(WorkflowRunRecord.workstream_syntheses),
                selectinload(WorkflowRunRecord.export_packages),
            )
        )
        return result.scalar_one_or_none()

    def _bundle_path(self, bundle_kind: str) -> str:
        mapping = {
            "executive_memo_markdown": "reports/executive_memo.md",
            "issue_register_markdown": "reports/issue_register.md",
            "workstream_synthesis_markdown": "reports/workstream_syntheses.md",
        }
        return mapping.get(bundle_kind, f"reports/{bundle_kind}.md")

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or Path(value).stem.lower() or "run-export"
