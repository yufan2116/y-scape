"""Base Tool Adapter — subprocess-only external project integration."""

from __future__ import annotations

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.integrations.config import ToolIntegrationConfig, record_run


class AdapterStatus:
    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"


class BaseToolAdapter(ABC):
    tool_id: str
    display_name: str
    description: str
    source_project: str
    category: str
    input_schema: dict[str, Any]
    input_summary: str = ""

    def __init__(self, config: ToolIntegrationConfig) -> None:
        self.config = config

    def metadata(self) -> dict[str, Any]:
        return {
            "toolId": self.tool_id,
            "displayName": self.config.display_name or self.display_name,
            "description": self.config.description or self.description,
            "sourceProject": self.config.source_project or self.source_project,
            "category": self.config.category or self.category,
            "inputSchema": self.input_schema,
            "inputSummary": self.input_summary,
            "enabled": self.config.enabled,
            "timeoutSeconds": self.config.timeout_seconds,
        }

    def validate_config(self) -> tuple[bool, str | None]:
        if not self.config.project_path.strip():
            return False, "project_path is required"
        project = Path(self.config.project_path)
        if not project.exists():
            return False, f"project_path does not exist: {self.config.project_path}"
        if not self.config.python_executable.strip():
            return False, "python_executable is required"
        exe = Path(self.config.python_executable)
        if not exe.exists():
            return False, f"python_executable does not exist: {self.config.python_executable}"
        if not self.config.entry_script.strip():
            return False, "entry_script is required"
        script = self._resolve_script_path()
        if script is None or not script.exists():
            return False, f"entry_script does not exist: {self.config.entry_script}"
        return True, None

    async def health_check(self) -> tuple[str, str | None]:
        if not self.config.project_path.strip() or not self.config.python_executable.strip():
            return AdapterStatus.NOT_CONFIGURED, "Not configured · Please set project path and executable."
        ok, err = self.validate_config()
        if not ok:
            return AdapterStatus.ERROR, err
        return await self._extended_health_check()

    async def _extended_health_check(self) -> tuple[str, str | None]:
        return AdapterStatus.READY, None

    @abstractmethod
    async def run(self, input_data: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        ...

    def _resolve_script_path(self) -> Path | None:
        script = Path(self.config.entry_script)
        if script.is_absolute():
            return script
        if self.config.working_directory.strip():
            return Path(self.config.working_directory) / script
        return Path(self.config.project_path) / script

    def _resolve_workdir(self) -> Path:
        if self.config.working_directory.strip():
            wd = Path(self.config.working_directory)
            if wd.exists():
                return wd
        return Path(self.config.project_path)

    async def _run_subprocess(
        self,
        extra_args: list[str] | None = None,
        *,
        dry_run: bool,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.config.enabled:
            return {"ok": False, "error": "Tool is disabled", "status": AdapterStatus.NOT_CONFIGURED}

        status, msg = await self.health_check()
        if status == AdapterStatus.NOT_CONFIGURED:
            return {"ok": False, "error": msg or "Tool not configured", "status": status}
        if status == AdapterStatus.ERROR:
            return {"ok": False, "error": msg or "Health check failed", "status": status}

        ok, err = self.validate_config()
        if not ok:
            return {"ok": False, "error": err, "status": AdapterStatus.ERROR}

        python_exe = str(Path(self.config.python_executable).resolve())
        script = str(self._resolve_script_path().resolve())  # type: ignore[union-attr]
        workdir = str(self._resolve_workdir().resolve())

        cmd = [python_exe, script]
        if dry_run:
            cmd.append("--dry-run")
        if extra_args:
            cmd.extend(extra_args)

        payload = json.dumps(input_data, ensure_ascii=False)
        timeout = float(self.config.timeout_seconds)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=payload.encode("utf-8")),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "ok": False,
                    "error": f"Process timed out after {self.config.timeout_seconds}s",
                    "status": AdapterStatus.ERROR,
                    "dryRun": dry_run,
                }

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            now = datetime.now(timezone.utc).isoformat()
            record_run(self.tool_id, now)

            result: dict[str, Any] = {
                "ok": proc.returncode == 0,
                "exitCode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "dryRun": dry_run,
                "ranAt": now,
            }
            if proc.returncode != 0:
                result["error"] = stderr.strip() or f"Process exited with code {proc.returncode}"
                result["status"] = AdapterStatus.ERROR
            else:
                result["status"] = AdapterStatus.READY
                try:
                    parsed = json.loads(stdout)
                    if isinstance(parsed, dict):
                        result["output"] = parsed
                except json.JSONDecodeError:
                    pass
            return result
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "status": AdapterStatus.ERROR,
                "dryRun": dry_run,
            }

    async def _stub_run(self, input_data: dict[str, Any], *, dry_run: bool, message: str) -> dict[str, Any]:
        """Phase-1 stub when paths are configured but real execution is deferred."""
        status, msg = await self.health_check()
        if status != AdapterStatus.READY:
            return {"ok": False, "error": msg or "Tool not ready", "status": status, "dryRun": dry_run}

        now = datetime.now(timezone.utc).isoformat()
        record_run(self.tool_id, now)
        return {
            "ok": True,
            "dryRun": dry_run,
            "status": AdapterStatus.READY,
            "message": message,
            "input": input_data,
            "ranAt": now,
        }


def default_python_executable() -> str:
    return sys.executable
