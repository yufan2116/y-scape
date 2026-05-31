import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from src.api.run_manager import RunManager
from src.main import app

@pytest.fixture
def isolated_runs_dir(tmp_path, monkeypatch):
    runs = tmp_path / "runs_active"
    runs.mkdir()
    monkeypatch.chdir(tmp_path)
    from src.api import run_manager as rm_mod
    from src.api.event_bus import clear_buses
    from src.api.status_snapshot import active_snapshots

    manager = rm_mod.RunManager(runs_dir=runs)
    monkeypatch.setattr(rm_mod, "run_manager", manager)
    active_snapshots.clear()
    clear_buses()
    yield runs
    active_snapshots.clear()
    clear_buses()

@pytest.fixture
def manager(isolated_runs_dir):
    from src.api.run_manager import run_manager
    return run_manager


@pytest.fixture
def isolated_tool_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    from src.integrations import config as cfg_mod
    from src.integrations.tool_registry import default_tool_registry

    monkeypatch.setattr(cfg_mod, "_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(cfg_mod, "_CONFIG_PATH", cfg_dir / "tool_integrations.json")
    monkeypatch.setattr(cfg_mod, "_RUN_HISTORY_PATH", cfg_dir / "tool_run_history.json")
    from src.system_settings import config as sys_cfg_mod

    monkeypatch.setattr(sys_cfg_mod, "_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(sys_cfg_mod, "_SETTINGS_PATH", cfg_dir / "system_settings.json")
    default_tool_registry.reload()
    yield cfg_dir


@pytest_asyncio.fixture
async def api_client(isolated_runs_dir, isolated_tool_config, monkeypatch):
    from src.api import run_manager as rm_mod
    from src.api.routes import tasks as tasks_routes

    mgr = RunManager(runs_dir=isolated_runs_dir)
    monkeypatch.setattr(rm_mod, "run_manager", mgr)
    monkeypatch.setattr(tasks_routes, "run_manager", mgr)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, mgr
