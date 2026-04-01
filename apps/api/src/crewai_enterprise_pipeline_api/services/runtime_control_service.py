from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.models import OrgRuntimeConfigRecord
from crewai_enterprise_pipeline_api.domain.models import (
    LlmModelOption,
    LlmProviderKind,
    LlmProviderSummary,
    OrgLlmRuntimeConfig,
    OrgLlmRuntimeConfigUpdate,
)

_OPENROUTER_CACHE_KEY = "runtime:openrouter:models:v1"
_OPENROUTER_MEMORY_CACHE: tuple[datetime, list[dict[str, Any]]] | None = None


class LlmRuntimeUnavailableError(RuntimeError):
    """Raised when a requested live LLM runtime cannot be satisfied."""


@dataclass(slots=True)
class ResolvedLlmRuntime:
    execution_mode: str
    effective_provider: str
    effective_model: str | None
    live_provider: str | None
    live_model: str | None
    source: str


class RuntimeControlService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_org_llm_default(self, org_id: str) -> OrgLlmRuntimeConfig:
        record = await self._get_or_create_runtime_config(org_id)
        await self.session.flush()
        return OrgLlmRuntimeConfig(
            org_id=record.org_id,
            llm_provider=record.llm_provider,
            llm_model=record.llm_model,
            updated_at=record.updated_at,
        )

    async def update_org_llm_default(
        self,
        org_id: str,
        payload: OrgLlmRuntimeConfigUpdate,
    ) -> OrgLlmRuntimeConfig:
        record = await self._get_or_create_runtime_config(org_id)

        provider = self._normalize_provider(payload.llm_provider)
        model = self._normalize_optional(payload.llm_model)

        if provider == LlmProviderKind.NONE.value:
            provider = None
            model = None

        if provider is None and model is not None:
            raise ValueError("An LLM model cannot be set without an LLM provider.")

        if provider not in {None, LlmProviderKind.OPENROUTER.value}:
            raise ValueError("Phase 19 only supports persisted org defaults for OpenRouter.")

        if provider == LlmProviderKind.OPENROUTER.value:
            if not self.settings.llm_api_key:
                raise LlmRuntimeUnavailableError(
                    "OpenRouter cannot be set as the org default because "
                    "LLM_API_KEY is not configured."
                )
            available_models = await self._fetch_openrouter_models()
            if not available_models:
                raise LlmRuntimeUnavailableError(
                    "OpenRouter is configured as the org default, but no eligible "
                    "models are available."
                )
            model_ids = {item.model_id for item in available_models}
            if model is None:
                model = available_models[0].model_id
            elif model not in model_ids:
                raise ValueError(f"OpenRouter model '{model}' is not available.")

        record.llm_provider = provider
        record.llm_model = model
        await self.session.commit()
        await self.session.refresh(record)
        return OrgLlmRuntimeConfig(
            org_id=record.org_id,
            llm_provider=record.llm_provider,
            llm_model=record.llm_model,
            updated_at=record.updated_at,
        )

    async def list_llm_providers(self) -> list[LlmProviderSummary]:
        providers = [
            LlmProviderSummary(
                provider=LlmProviderKind.NONE.value,
                label="Deterministic Fallback",
                configured=True,
                available=True,
                detail="Run the deterministic pipeline without a live LLM provider.",
                models=[],
            )
        ]

        if not self.settings.llm_api_key:
            providers.append(
                LlmProviderSummary(
                    provider=LlmProviderKind.OPENROUTER.value,
                    label="OpenRouter",
                    configured=False,
                    available=False,
                    detail="OpenRouter is not configured because LLM_API_KEY is missing.",
                    models=[],
                )
            )
            return providers

        try:
            models = await self._fetch_openrouter_models()
        except Exception as exc:  # noqa: BLE001
            providers.append(
                LlmProviderSummary(
                    provider=LlmProviderKind.OPENROUTER.value,
                    label="OpenRouter",
                    configured=True,
                    available=False,
                    detail=f"OpenRouter catalog lookup failed: {exc}",
                    models=[],
                )
            )
            return providers

        providers.append(
            LlmProviderSummary(
                provider=LlmProviderKind.OPENROUTER.value,
                label="OpenRouter",
                configured=True,
                available=bool(models),
                detail=(
                    f"OpenRouter returned {len(models)} eligible tool-capable text models."
                    if models
                    else "OpenRouter returned no eligible tool-capable text models."
                ),
                models=models,
            )
        )
        return providers

    async def resolve_run_runtime(
        self,
        *,
        org_id: str,
        llm_provider_override: str | None,
        llm_model_override: str | None,
    ) -> ResolvedLlmRuntime:
        org_config = await self._get_or_create_runtime_config(org_id)

        override_provider = self._normalize_provider(llm_provider_override)
        override_model = self._normalize_optional(llm_model_override)
        org_provider = self._normalize_provider(org_config.llm_provider)
        org_model = self._normalize_optional(org_config.llm_model)
        env_provider = self._normalize_provider(self.settings.llm_provider)
        env_model = self._normalize_optional(self.settings.llm_model)

        if override_provider is not None or override_model is not None:
            source = "override"
            provider = (
                override_provider
                or org_provider
                or env_provider
                or LlmProviderKind.NONE.value
            )
            model = override_model or org_model or env_model
        elif org_provider is not None:
            source = "org_default"
            provider = org_provider
            model = org_model or env_model
        else:
            source = "environment"
            provider = env_provider or LlmProviderKind.NONE.value
            model = env_model

        if provider in {None, "", LlmProviderKind.NONE.value}:
            return ResolvedLlmRuntime(
                execution_mode="deterministic",
                effective_provider="deterministic",
                effective_model=None,
                live_provider=None,
                live_model=None,
                source=source,
            )

        if source in {"override", "org_default"} and provider != LlmProviderKind.OPENROUTER.value:
            raise LlmRuntimeUnavailableError(
                f"Explicit runtime provider '{provider}' is not supported in Phase 19."
            )

        if provider == LlmProviderKind.OPENROUTER.value:
            if not self.settings.llm_api_key:
                if source == "environment":
                    return ResolvedLlmRuntime(
                        execution_mode="deterministic",
                        effective_provider="deterministic",
                        effective_model=None,
                        live_provider=None,
                        live_model=None,
                        source="environment_fallback",
                    )
                raise LlmRuntimeUnavailableError(
                    "OpenRouter was requested, but LLM_API_KEY is not configured."
                )

            models = await self._fetch_openrouter_models()
            if not models:
                if source == "environment":
                    return ResolvedLlmRuntime(
                        execution_mode="deterministic",
                        effective_provider="deterministic",
                        effective_model=None,
                        live_provider=None,
                        live_model=None,
                        source="environment_fallback",
                    )
                raise LlmRuntimeUnavailableError(
                    "OpenRouter was requested, but no eligible tool-capable "
                    "text models were returned."
                )

            model_ids = {item.model_id for item in models}
            if model is None:
                model = models[0].model_id
            if model not in model_ids:
                if source == "environment":
                    return ResolvedLlmRuntime(
                        execution_mode="deterministic",
                        effective_provider="deterministic",
                        effective_model=None,
                        live_provider=None,
                        live_model=None,
                        source="environment_fallback",
                    )
                raise LlmRuntimeUnavailableError(
                    f"OpenRouter model '{model}' is not available."
                )

            return ResolvedLlmRuntime(
                execution_mode="crew",
                effective_provider=LlmProviderKind.OPENROUTER.value,
                effective_model=model,
                live_provider=LlmProviderKind.OPENROUTER.value,
                live_model=model,
                source=source,
            )

        if source != "environment":
            raise LlmRuntimeUnavailableError(
                f"Provider '{provider}' is unsupported for explicit runtime control."
            )

        if not self.settings.llm_api_key:
            return ResolvedLlmRuntime(
                execution_mode="deterministic",
                effective_provider="deterministic",
                effective_model=None,
                live_provider=None,
                live_model=None,
                source="environment_fallback",
            )

        return ResolvedLlmRuntime(
            execution_mode="crew",
            effective_provider=provider,
            effective_model=model or self.settings.llm_model,
            live_provider=provider,
            live_model=model or self.settings.llm_model,
            source=source,
        )

    async def _get_or_create_runtime_config(self, org_id: str) -> OrgRuntimeConfigRecord:
        result = await self.session.execute(
            select(OrgRuntimeConfigRecord).where(OrgRuntimeConfigRecord.org_id == org_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = OrgRuntimeConfigRecord(org_id=org_id, llm_provider=None, llm_model=None)
            self.session.add(record)
            await self.session.flush()
        return record

    async def _fetch_openrouter_models(self) -> list[LlmModelOption]:
        cached = await self._get_cached_model_payload()
        if cached is not None:
            return self._deserialize_model_options(cached)

        url = self._openrouter_models_url()
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(
            timeout=self.settings.dependency_probe_timeout_seconds
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data", []) if isinstance(payload, dict) else []
        models = self._extract_model_options(data)
        await self._cache_model_payload([item.model_dump() for item in models])
        return models

    async def _get_cached_model_payload(self) -> list[dict[str, Any]] | None:
        global _OPENROUTER_MEMORY_CACHE

        now = datetime.now(UTC)
        if _OPENROUTER_MEMORY_CACHE is not None:
            expires_at, payload = _OPENROUTER_MEMORY_CACHE
            if expires_at > now:
                return payload

        client = await self._redis_client()
        if client is None:
            return None

        try:
            raw = await client.get(_OPENROUTER_CACHE_KEY)
            if not raw:
                return None
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return None
        finally:
            await client.aclose()

    async def _cache_model_payload(self, payload: list[dict[str, Any]]) -> None:
        global _OPENROUTER_MEMORY_CACHE

        expires_at = datetime.now(UTC) + timedelta(
            seconds=self.settings.llm_model_catalog_cache_seconds
        )
        _OPENROUTER_MEMORY_CACHE = (expires_at, payload)

        client = await self._redis_client()
        if client is None:
            return
        try:
            await client.setex(
                _OPENROUTER_CACHE_KEY,
                self.settings.llm_model_catalog_cache_seconds,
                json.dumps(payload),
            )
        except Exception:  # noqa: BLE001
            return
        finally:
            await client.aclose()

    async def _redis_client(self) -> Redis | None:
        client: Redis | None = None
        try:
            client = Redis.from_url(self.settings.redis_url, socket_timeout=2)
            await client.ping()
            return client
        except Exception:  # noqa: BLE001
            try:
                if client is not None:
                    await client.aclose()
            except Exception:  # noqa: BLE001
                pass
            return None

    def _extract_model_options(self, payload: list[dict[str, Any]]) -> list[LlmModelOption]:
        models: list[LlmModelOption] = []
        for item in payload:
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue

            supported_parameters = {
                str(param).lower() for param in item.get("supported_parameters", []) or []
            }
            tool_calling_supported = bool(
                {"tools", "tool_choice", "function_call", "parallel_tool_calls"}
                & supported_parameters
            )
            if not tool_calling_supported:
                continue

            output_modalities = self._extract_output_modalities(item)
            text_output_supported = not output_modalities or "text" in output_modalities
            if not text_output_supported:
                continue

            models.append(
                LlmModelOption(
                    model_id=model_id,
                    label=str(item.get("name") or model_id),
                    provider=LlmProviderKind.OPENROUTER.value,
                    tool_calling_supported=True,
                    text_output_supported=True,
                    context_length=self._extract_context_length(item),
                    pricing_summary=self._extract_pricing_summary(item),
                )
            )

        models.sort(key=lambda item: item.label.lower())
        return models

    def _extract_output_modalities(self, item: dict[str, Any]) -> set[str]:
        output_modalities = item.get("output_modalities")
        if not output_modalities and isinstance(item.get("architecture"), dict):
            output_modalities = item["architecture"].get("output_modalities")
        if not output_modalities:
            modality = None
            if isinstance(item.get("architecture"), dict):
                modality = item["architecture"].get("modality")
            if modality:
                output_modalities = [modality]
        return {str(modality).lower() for modality in output_modalities or []}

    def _extract_context_length(self, item: dict[str, Any]) -> int | None:
        value = item.get("context_length")
        if value is None and isinstance(item.get("top_provider"), dict):
            value = item["top_provider"].get("context_length")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _extract_pricing_summary(self, item: dict[str, Any]) -> str | None:
        pricing = item.get("pricing")
        if not isinstance(pricing, dict):
            return None
        prompt = pricing.get("prompt")
        completion = pricing.get("completion")
        if prompt is None and completion is None:
            return None
        return f"prompt={prompt or 'n/a'} | completion={completion or 'n/a'}"

    def _deserialize_model_options(self, payload: list[dict[str, Any]]) -> list[LlmModelOption]:
        return [LlmModelOption.model_validate(item) for item in payload]

    def _openrouter_models_url(self) -> str:
        base_url = (self.settings.llm_base_url or "https://openrouter.ai/api/v1").rstrip("/")
        if base_url.endswith("/models"):
            return base_url
        return f"{base_url}/models"

    def _normalize_provider(self, value: str | None) -> str | None:
        normalized = self._normalize_optional(value)
        return normalized.lower() if normalized is not None else None

    def _normalize_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
