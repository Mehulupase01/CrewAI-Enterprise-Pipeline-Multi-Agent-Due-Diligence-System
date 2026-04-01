from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_SRC = PROJECT_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from crewai_enterprise_pipeline_api.main import create_app


def _render_parameters(parameters: list[dict]) -> list[str]:
    if not parameters:
        return ["None"]
    lines: list[str] = []
    for parameter in parameters:
        name = parameter.get("name", "unknown")
        required = "required" if parameter.get("required") else "optional"
        location = parameter.get("in", "unknown")
        schema = parameter.get("schema", {}) or {}
        schema_type = schema.get("type", schema.get("$ref", "object"))
        description = parameter.get("description", "")
        suffix = f": {description}" if description else ""
        lines.append(f"- `{name}` ({location}, {schema_type}, {required}){suffix}")
    return lines


def _render_request_body(request_body: dict | None) -> list[str]:
    if not request_body:
        return ["None"]
    lines: list[str] = []
    content = request_body.get("content", {}) or {}
    for media_type, schema_payload in content.items():
        schema = schema_payload.get("schema", {}) or {}
        schema_name = schema.get("$ref", schema.get("type", "object"))
        lines.append(f"- `{media_type}` -> `{schema_name}`")
    return lines or ["None"]


def _render_responses(responses: dict) -> list[str]:
    lines: list[str] = []
    for status_code, response in responses.items():
        description = response.get("description", "")
        lines.append(f"- `{status_code}`: {description or 'No description'}")
    return lines or ["None"]


def generate_api_reference_markdown() -> str:
    app = create_app()
    schema = app.openapi()
    info = schema.get("info", {})
    paths = schema.get("paths", {})

    lines = [
        f"# {info.get('title', 'API Reference')}",
        "",
        "## Overview",
        "",
        f"- Version: `{info.get('version', 'unknown')}`",
        f"- OpenAPI spec: `{app.openapi_url}`",
        f"- Interactive docs: `{app.docs_url}`",
        "",
        "## Endpoints",
        "",
    ]

    for path in sorted(paths):
        operations = paths[path]
        for method in sorted(operations):
            operation = operations[method]
            operation_id = operation.get("operationId", f"{method}_{path}")
            summary = operation.get("summary") or operation.get("description") or "No summary provided."
            tags = ", ".join(operation.get("tags", [])) or "untagged"
            lines.extend(
                [
                    f"### `{method.upper()} {path}`",
                    "",
                    f"- Operation ID: `{operation_id}`",
                    f"- Tags: `{tags}`",
                    f"- Summary: {summary}",
                    "",
                    "**Parameters**",
                    "",
                    *_render_parameters(operation.get("parameters", [])),
                    "",
                    "**Request Body**",
                    "",
                    *_render_request_body(operation.get("requestBody")),
                    "",
                    "**Responses**",
                    "",
                    *_render_responses(operation.get("responses", {})),
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the API reference markdown from OpenAPI.")
    parser.add_argument("--output", required=True, help="Output markdown file path.")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_api_reference_markdown(), encoding="utf-8")
    print(f"Generated API reference at {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
