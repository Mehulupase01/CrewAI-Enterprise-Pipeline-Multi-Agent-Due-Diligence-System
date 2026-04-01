from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.core.telemetry import observe_dependency_probe
from crewai_enterprise_pipeline_api.db.models import DependencyStatusRecord
from crewai_enterprise_pipeline_api.db.session import get_database
from crewai_enterprise_pipeline_api.domain.models import (
    DependencyCategory,
    DependencyMode,
    DependencyState,
    DependencyStatusEntry,
    DependencyStatusReport,
)
from crewai_enterprise_pipeline_api.source_adapters import get_registered_adapters
from crewai_enterprise_pipeline_api.source_adapters.base import BaseSourceAdapter
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService


class DependencyProbeService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.storage = DocumentStorageService()

    async def build_report(self) -> DependencyStatusReport:
        dependencies = await self.probe_all()
        overall_status = self._overall_status(dependencies)
        return DependencyStatusReport(
            status=overall_status.value,
            environment=self.settings.app_env,
            timestamp=datetime.now(UTC),
            auth_required=self.settings.auth_required,
            dependencies=dependencies,
        )

    async def refresh_and_persist(self) -> DependencyStatusReport:
        report = await self.build_report()
        if self.session is not None:
            await self._persist_with_session(self.session, report.dependencies)
        else:
            database = get_database()
            async with database.session_factory() as session:
                session.info["skip_audit"] = True
                await self._persist_with_session(session, report.dependencies)
        return report

    async def get_latest_report(self) -> DependencyStatusReport:
        if self.session is not None:
            dependencies = await self._load_persisted(self.session)
        else:
            database = get_database()
            async with database.session_factory() as session:
                dependencies = await self._load_persisted(session)

        if not dependencies:
            return await self.refresh_and_persist()

        return DependencyStatusReport(
            status=self._overall_status(dependencies).value,
            environment=self.settings.app_env,
            timestamp=max(item.last_checked_at for item in dependencies),
            auth_required=self.settings.auth_required,
            dependencies=dependencies,
        )

    async def probe_all(self) -> list[DependencyStatusEntry]:
        dependencies = [
            await self._probe_database(),
            await self._probe_redis(),
            await self._probe_storage(),
            await self._probe_llm(),
        ]
        for adapter in get_registered_adapters():
            dependencies.append(await self._probe_source_adapter(adapter))
        return dependencies

    async def _probe_database(self) -> DependencyStatusEntry:
        return await self._probe(
            name="database",
            category=DependencyCategory.INFRA,
            mode=DependencyMode.LIVE,
            failure_state=DependencyState.FAILED,
            probe=self._run_database_probe,
        )

    async def _probe_redis(self) -> DependencyStatusEntry:
        checked_at = datetime.now(UTC)
        start = perf_counter()
        try:
            with observe_dependency_probe(dependency_name="redis"):
                detail = await self._run_redis_probe()
            return DependencyStatusEntry(
                name="redis",
                category=DependencyCategory.INFRA,
                mode=DependencyMode.LIVE,
                status=DependencyState.OK,
                detail=detail,
                latency_ms=round((perf_counter() - start) * 1000, 2),
                last_checked_at=checked_at,
                last_success_at=checked_at,
            )
        except Exception as exc:  # noqa: BLE001
            if self.settings.app_env == "production":
                status = DependencyState.FAILED
                detail = "Redis probe failed."
            else:
                status = DependencyState.OK
                detail = "Redis unavailable; runtime will fall back to in-memory rate limiting."
            return DependencyStatusEntry(
                name="redis",
                category=DependencyCategory.INFRA,
                mode=(
                    DependencyMode.DISABLED
                    if status == DependencyState.OK
                    else DependencyMode.LIVE
                ),
                status=status,
                detail=detail,
                latency_ms=round((perf_counter() - start) * 1000, 2),
                last_checked_at=checked_at,
                last_success_at=checked_at if status == DependencyState.OK else None,
                failure_reason=None if status == DependencyState.OK else str(exc),
            )

    async def _probe_storage(self) -> DependencyStatusEntry:
        return await self._probe(
            name="storage",
            category=DependencyCategory.INFRA,
            mode=DependencyMode.LIVE,
            failure_state=DependencyState.FAILED,
            probe=self._run_storage_probe,
        )

    async def _probe_llm(self) -> DependencyStatusEntry:
        checked_at = datetime.now(UTC)
        provider = self.settings.llm_provider.lower()
        if provider == "none":
            return DependencyStatusEntry(
                name="openrouter",
                category=DependencyCategory.LLM,
                mode=DependencyMode.DISABLED,
                status=DependencyState.OK,
                detail="LLM mode is disabled; deterministic workflow fallback remains active.",
                latency_ms=0.0,
                last_checked_at=checked_at,
                last_success_at=checked_at,
            )

        if provider != "openrouter":
            mode = DependencyMode.LIVE if self.settings.llm_api_key else DependencyMode.UNCONFIGURED
            status = (
                DependencyState.OK
                if self.settings.llm_api_key
                else (
                    DependencyState.FAILED
                    if self.settings.app_env == "production"
                    else DependencyState.DEGRADED
                )
            )
            detail = (
                f"Provider '{provider}' is configured outside the OpenRouter-first path."
                if self.settings.llm_api_key
                else f"Provider '{provider}' has no API key configured."
            )
            return DependencyStatusEntry(
                name="llm_provider",
                category=DependencyCategory.LLM,
                mode=mode,
                status=status,
                detail=detail,
                latency_ms=0.0,
                last_checked_at=checked_at,
                last_success_at=checked_at if status == DependencyState.OK else None,
                failure_reason=None if status == DependencyState.OK else detail,
            )

        if not self.settings.llm_api_key:
            status = (
                DependencyState.FAILED
                if self.settings.app_env == "production"
                else DependencyState.DEGRADED
            )
            return DependencyStatusEntry(
                name="openrouter",
                category=DependencyCategory.LLM,
                mode=DependencyMode.UNCONFIGURED,
                status=status,
                detail="OpenRouter is selected but no API key is configured.",
                latency_ms=0.0,
                last_checked_at=checked_at,
                failure_reason="Missing LLM_API_KEY.",
            )

        return await self._probe(
            name="openrouter",
            category=DependencyCategory.LLM,
            mode=DependencyMode.LIVE,
            failure_state=(
                DependencyState.FAILED
                if self.settings.app_env == "production"
                else DependencyState.DEGRADED
            ),
            probe=self._run_openrouter_probe,
        )

    async def _probe_source_adapter(self, adapter: BaseSourceAdapter) -> DependencyStatusEntry:
        checked_at = datetime.now(UTC)
        adapter_status = adapter.get_status(self.settings)

        if adapter_status.value == "stub":
            return DependencyStatusEntry(
                name=adapter.adapter_id,
                category=self._adapter_category(adapter),
                mode=DependencyMode.STUB,
                status=DependencyState.OK,
                detail=f"{adapter.name} is operating in stub mode for {self.settings.app_env}.",
                latency_ms=0.0,
                last_checked_at=checked_at,
                last_success_at=checked_at,
            )

        if adapter_status.value == "unavailable":
            failure_state = (
                DependencyState.FAILED
                if self.settings.app_env == "production"
                else DependencyState.DEGRADED
            )
            detail = f"{adapter.name} has no live configuration in {self.settings.app_env}."
            return DependencyStatusEntry(
                name=adapter.adapter_id,
                category=self._adapter_category(adapter),
                mode=DependencyMode.UNCONFIGURED,
                status=failure_state,
                detail=detail,
                latency_ms=0.0,
                last_checked_at=checked_at,
                failure_reason=detail,
            )

        return await self._probe(
            name=adapter.adapter_id,
            category=self._adapter_category(adapter),
            mode=DependencyMode.LIVE,
            failure_state=(
                DependencyState.FAILED
                if self.settings.app_env == "production"
                else DependencyState.DEGRADED
            ),
            probe=lambda: self._run_adapter_probe(adapter),
        )

    async def _probe(
        self,
        *,
        name: str,
        category: DependencyCategory,
        mode: DependencyMode,
        failure_state: DependencyState,
        probe,
    ) -> DependencyStatusEntry:
        checked_at = datetime.now(UTC)
        start = perf_counter()
        detail = ""
        last_success_at: datetime | None = None
        failure_reason: str | None = None
        status = DependencyState.OK

        try:
            with observe_dependency_probe(dependency_name=name):
                detail = await probe()
            last_success_at = checked_at
        except Exception as exc:  # noqa: BLE001
            status = failure_state
            detail = f"{name} probe failed."
            failure_reason = str(exc)

        return DependencyStatusEntry(
            name=name,
            category=category,
            mode=mode,
            status=status,
            detail=detail if failure_reason is None else f"{detail} {failure_reason}".strip(),
            latency_ms=round((perf_counter() - start) * 1000, 2),
            last_checked_at=checked_at,
            last_success_at=last_success_at,
            failure_reason=failure_reason,
        )

    async def _run_database_probe(self) -> str:
        if self.session is not None:
            await self.session.execute(text("SELECT 1"))
            return "Database connection succeeded via request session."

        database = get_database()
        async with database.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "Database connection succeeded via pooled runtime session."

    async def _run_redis_probe(self) -> str:
        client = Redis.from_url(self.settings.redis_url, socket_timeout=2)
        try:
            pong = await client.ping()
            if not pong:
                raise RuntimeError("Redis ping returned falsy response.")
        finally:
            await client.aclose()
        return (
            "Redis ping succeeded against "
            f"{self.settings.redis_host}:{self.settings.redis_port}."
        )

    async def _run_storage_probe(self) -> str:
        backend = self.settings.storage_backend.lower()
        if backend == "local":
            root = Path(self.settings.local_storage_root).resolve()
            root.mkdir(parents=True, exist_ok=True)
            return f"Local storage available at {root}."

        client = self.storage._s3_client()
        bucket = self.settings.minio_bucket_name
        try:
            client.head_bucket(Bucket=bucket)
            return f"S3-compatible bucket '{bucket}' is reachable."
        except ClientError:
            if backend == "auto":
                root = Path(self.settings.local_storage_root).resolve()
                root.mkdir(parents=True, exist_ok=True)
                return (
                    f"S3 probe failed for bucket '{bucket}', "
                    f"but local fallback root is ready at {root}."
                )
            raise
        except BotoCoreError:
            if backend == "auto":
                root = Path(self.settings.local_storage_root).resolve()
                root.mkdir(parents=True, exist_ok=True)
                return (
                    f"S3 probe failed for endpoint {self.settings.minio_endpoint}, "
                    f"local fallback root is ready at {root}."
                )
            raise

    async def _run_openrouter_probe(self) -> str:
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        url = self._openrouter_models_url()
        async with httpx.AsyncClient(
            timeout=self.settings.dependency_probe_timeout_seconds
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
        model_count = len(payload.get("data", [])) if isinstance(payload, dict) else 0
        return f"OpenRouter models endpoint reachable with {model_count} listed models."

    async def _run_adapter_probe(self, adapter: BaseSourceAdapter) -> str:
        if adapter.adapter_id == "sanctions":
            urls = [
                self.settings.sanctions_ofac_url,
                self.settings.sanctions_mca_url,
                self.settings.sanctions_sebi_url,
            ]
            statuses = [await self._check_http_target(url) for url in urls if url]
            return f"Sanctions feeds reachable ({'; '.join(statuses)})."

        if adapter.base_url_setting_name is None:
            return f"{adapter.name} is available without a probeable base URL."

        base_url = getattr(self.settings, adapter.base_url_setting_name, None)
        if not base_url:
            raise RuntimeError(f"{adapter.adapter_id} base URL is missing.")

        status = await self._check_http_target(base_url)
        return f"{adapter.name} endpoint reachable ({status})."

    async def _check_http_target(self, url: str) -> str:
        if not url:
            raise RuntimeError("HTTP target URL is missing.")
        async with httpx.AsyncClient(
            timeout=self.settings.dependency_probe_timeout_seconds
        ) as client:
            response = await client.request("HEAD", url)
            if response.status_code == 405:
                response = await client.get(url)
            if response.status_code >= 500:
                raise RuntimeError(f"{response.status_code} from {url}")
        return f"{response.status_code} from {url}"

    def _adapter_category(self, adapter: BaseSourceAdapter) -> DependencyCategory:
        if adapter.adapter_id == "sanctions":
            return DependencyCategory.FEED
        if adapter.adapter_id == "cibil":
            return DependencyCategory.VENDOR
        return DependencyCategory.REGISTRY

    def _adapter_mode(self, adapter: BaseSourceAdapter) -> DependencyMode:
        adapter_status = adapter.get_status(self.settings)
        if adapter_status.value == "stub":
            return DependencyMode.STUB
        if adapter_status.value == "unavailable":
            return DependencyMode.UNCONFIGURED
        return DependencyMode.LIVE

    async def _persist_with_session(
        self,
        session: AsyncSession,
        dependencies: list[DependencyStatusEntry],
    ) -> None:
        result = await session.execute(select(DependencyStatusRecord))
        existing = {
            item.dependency_name: item
            for item in result.scalars().all()
        }
        seen_names = set()

        for dependency in dependencies:
            seen_names.add(dependency.name)
            record = existing.get(dependency.name)
            if record is None:
                record = DependencyStatusRecord(dependency_name=dependency.name)
                session.add(record)

            record.category = dependency.category.value
            record.mode = dependency.mode.value
            record.status = dependency.status.value
            record.detail = dependency.detail
            record.latency_ms = dependency.latency_ms
            record.last_checked_at = dependency.last_checked_at
            record.last_success_at = dependency.last_success_at
            record.failure_reason = dependency.failure_reason

        for dependency_name, record in existing.items():
            if dependency_name not in seen_names:
                await session.delete(record)

        await session.commit()

    async def _load_persisted(self, session: AsyncSession) -> list[DependencyStatusEntry]:
        result = await session.execute(
            select(DependencyStatusRecord).order_by(DependencyStatusRecord.dependency_name.asc())
        )
        return [
            DependencyStatusEntry(
                name=item.dependency_name,
                category=DependencyCategory(item.category),
                mode=DependencyMode(item.mode),
                status=DependencyState(item.status),
                detail=item.detail,
                latency_ms=item.latency_ms,
                last_checked_at=item.last_checked_at,
                last_success_at=item.last_success_at,
                failure_reason=item.failure_reason,
            )
            for item in result.scalars().all()
        ]

    def _openrouter_models_url(self) -> str:
        if self.settings.llm_base_url:
            base = self.settings.llm_base_url.rstrip("/")
            if base.endswith("/models"):
                return base
            return f"{base}/models"
        return "https://openrouter.ai/api/v1/models"

    def _overall_status(self, dependencies: list[DependencyStatusEntry]) -> DependencyState:
        if any(item.status == DependencyState.FAILED for item in dependencies):
            return DependencyState.FAILED
        if any(item.status == DependencyState.DEGRADED for item in dependencies):
            return DependencyState.DEGRADED
        return DependencyState.OK
