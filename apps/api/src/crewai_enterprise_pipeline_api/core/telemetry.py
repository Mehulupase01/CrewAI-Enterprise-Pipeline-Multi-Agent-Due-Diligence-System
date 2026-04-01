from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy.ext.asyncio import AsyncEngine

from crewai_enterprise_pipeline_api.core.settings import Settings

HTTP_REQUESTS_TOTAL = Counter(
    "cep_http_requests_total",
    "Total HTTP requests handled by the API.",
    ("method", "route", "status_code"),
)
HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "cep_http_request_latency_seconds",
    "Latency for HTTP requests handled by the API.",
    ("method", "route", "status_code"),
)
WORKFLOW_DURATION_SECONDS = Histogram(
    "cep_workflow_duration_seconds",
    "Latency for workflow execution.",
    ("execution_mode", "status"),
)
DOCUMENT_PARSE_DURATION_SECONDS = Histogram(
    "cep_document_parse_duration_seconds",
    "Latency for document parsing.",
    ("parser_name", "status"),
)
DOCUMENT_INGESTION_DURATION_SECONDS = Histogram(
    "cep_document_ingestion_duration_seconds",
    "Latency for document ingestion.",
    ("source_kind", "status"),
)
CONNECTOR_FETCH_DURATION_SECONDS = Histogram(
    "cep_connector_fetch_duration_seconds",
    "Latency for source-adapter fetch operations.",
    ("adapter_key", "status"),
)
CONNECTOR_FETCH_FAILURES_TOTAL = Counter(
    "cep_connector_fetch_failures_total",
    "Failures encountered during source-adapter fetch operations.",
    ("adapter_key",),
)
EXPORT_GENERATION_DURATION_SECONDS = Histogram(
    "cep_export_generation_duration_seconds",
    "Latency for report export package generation.",
    ("format", "status"),
)
LLM_RUN_DURATION_SECONDS = Histogram(
    "cep_llm_run_duration_seconds",
    "Latency for CrewAI/LLM-backed workflow execution.",
    ("provider", "model", "status"),
)
LLM_RUN_FAILURES_TOTAL = Counter(
    "cep_llm_run_failures_total",
    "Failures encountered while executing LLM-backed workflow runs.",
    ("provider", "model"),
)
DEPENDENCY_PROBE_DURATION_SECONDS = Histogram(
    "cep_dependency_probe_duration_seconds",
    "Latency for dependency health probes.",
    ("dependency", "status"),
)
DEPENDENCY_PROBE_FAILURES_TOTAL = Counter(
    "cep_dependency_probe_failures_total",
    "Failures encountered while probing external dependencies.",
    ("dependency",),
)

_TRACING_INITIALIZED = False
_HTTPX_INSTRUMENTOR = HTTPXClientInstrumentor()
_SQLALCHEMY_INSTRUMENTOR = SQLAlchemyInstrumentor()
_FASTAPI_APPS: set[int] = set()


def initialize_observability(
    *,
    settings: Settings,
    app: FastAPI | None = None,
    engine: AsyncEngine | None = None,
) -> None:
    global _TRACING_INITIALIZED

    if not settings.observability_enabled:
        return

    if not _TRACING_INITIALIZED:
        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": settings.app_version,
                "deployment.environment": settings.app_env,
            }
        )
        provider = TracerProvider(resource=resource)
        if settings.otel_exporter_otlp_endpoint:
            exporter = OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _TRACING_INITIALIZED = True

    if engine is not None:
        sync_engine = engine.sync_engine
        if not _SQLALCHEMY_INSTRUMENTOR.is_instrumented_by_opentelemetry:
            _SQLALCHEMY_INSTRUMENTOR.instrument(engine=sync_engine)

    if not _HTTPX_INSTRUMENTOR.is_instrumented_by_opentelemetry:
        _HTTPX_INSTRUMENTOR.instrument()

    if app is not None and id(app) not in _FASTAPI_APPS:
        excluded_urls = ",".join(
            [
                f"{settings.api_prefix}/docs",
                f"{settings.api_prefix}/openapi.json",
                f"{settings.api_prefix}/metrics",
            ]
        )
        FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded_urls)
        _FASTAPI_APPS.add(id(app))


def render_metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def record_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    status = str(status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status_code=status).inc()
    HTTP_REQUEST_LATENCY_SECONDS.labels(
        method=method,
        route=route,
        status_code=status,
    ).observe(duration_seconds)


def record_document_parse(*, parser_name: str, duration_seconds: float, success: bool) -> None:
    status = "ok" if success else "error"
    DOCUMENT_PARSE_DURATION_SECONDS.labels(parser_name=parser_name, status=status).observe(
        duration_seconds
    )


@contextmanager
def observe_workflow_run(*, execution_mode: str) -> Any:
    with _observe_histogram(
        "workflow.execute",
        WORKFLOW_DURATION_SECONDS,
        labels={"execution_mode": execution_mode},
    ):
        yield


@contextmanager
def observe_document_ingestion(*, source_kind: str) -> Any:
    with _observe_histogram(
        "document.ingestion",
        DOCUMENT_INGESTION_DURATION_SECONDS,
        labels={"source_kind": source_kind},
    ):
        yield


@contextmanager
def observe_connector_fetch(*, adapter_key: str) -> Any:
    try:
        with _observe_histogram(
            "connector.fetch",
            CONNECTOR_FETCH_DURATION_SECONDS,
            labels={"adapter_key": adapter_key},
        ):
            yield
    except Exception:
        CONNECTOR_FETCH_FAILURES_TOTAL.labels(adapter_key=adapter_key).inc()
        raise


@contextmanager
def observe_export_generation(*, format_name: str) -> Any:
    with _observe_histogram(
        "export.generate",
        EXPORT_GENERATION_DURATION_SECONDS,
        labels={"format": format_name},
    ):
        yield


@contextmanager
def observe_llm_run(*, provider: str, model: str) -> Any:
    try:
        with _observe_histogram(
            "llm.run",
            LLM_RUN_DURATION_SECONDS,
            labels={"provider": provider, "model": model},
        ):
            yield
    except Exception:
        LLM_RUN_FAILURES_TOTAL.labels(provider=provider, model=model).inc()
        raise


@contextmanager
def observe_dependency_probe(*, dependency_name: str) -> Any:
    try:
        with _observe_histogram(
            "dependency.probe",
            DEPENDENCY_PROBE_DURATION_SECONDS,
            labels={"dependency": dependency_name},
        ):
            yield
    except Exception:
        DEPENDENCY_PROBE_FAILURES_TOTAL.labels(dependency=dependency_name).inc()
        raise


def get_tracer(name: str = "crewai_enterprise_pipeline_api"):
    return trace.get_tracer(name)


@contextmanager
def _observe_histogram(
    span_name: str,
    histogram: Histogram,
    *,
    labels: Mapping[str, str],
) -> Any:
    tracer = get_tracer()
    start = perf_counter()
    status = "ok"
    with tracer.start_as_current_span(span_name) as span:
        for key, value in labels.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            status = "error"
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        else:
            span.set_status(Status(StatusCode.OK))
        finally:
            elapsed = perf_counter() - start
            histogram.labels(status=status, **labels).observe(elapsed)
