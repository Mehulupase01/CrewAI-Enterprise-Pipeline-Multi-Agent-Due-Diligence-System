from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_generate_api_reference_script_writes_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "api-reference.md"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "generate_api_reference.py"),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    content = output_path.read_text(encoding="utf-8")
    assert "# CrewAI Enterprise Pipeline" in content
    assert "`POST /api/v1/auth/token`" in content
    assert "`GET /api/v1/health/liveness`" in content


def test_backup_script_dry_run_outputs_backup_plan() -> None:
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "backup-db.ps1"),
            "-DryRun",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["backup_file"].endswith(".sql")
    assert payload["postgres_db"] == "crewai_pipeline"
    assert payload["retention_days"] == 30


def test_restore_script_dry_run_outputs_restore_plan(tmp_path: Path) -> None:
    backup_file = tmp_path / "backup.sql"
    backup_file.write_text("-- test backup", encoding="utf-8")

    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "restore-db.ps1"),
            "-BackupFile",
            str(backup_file),
            "-DryRun",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["backup_file"].endswith("backup.sql")
    assert payload["postgres_db"] == "crewai_pipeline"


def test_production_compose_config_is_valid() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(REPO_ROOT / "docker-compose.prod.yml"), "config"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "services:" in result.stdout
    assert "migrate:" in result.stdout
    assert "grafana:" in result.stdout


def test_validate_prod_stack_script_skips_cleanly_without_daemon() -> None:
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "validate-prod-stack.ps1"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Skipping live production stack validation" in result.stdout
