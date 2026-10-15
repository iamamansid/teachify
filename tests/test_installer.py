"""Tests for `teachify install` / `uninstall` — multi-client auto-registration."""

import json
from pathlib import Path

import pytest

from teachify import installer


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    d = tmp_path / "proj"
    d.mkdir()
    monkeypatch.chdir(d)
    return d


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_install_registers_all_clients(fake_home, workdir):
    results = installer.install()
    assert results["claude code"] == "added"
    assert results["cursor"] == "added"
    assert results["copilot cli"] == "added"
    assert results["codex"] == "added"
    assert results["vscode (this project)"] == "added"
    assert results["/teach slash command"] == "added"

    assert _json(fake_home / ".claude.json")["mcpServers"]["teachify"] == {
        "command": "teachify",
        "args": [],
    }
    assert _json(fake_home / ".cursor" / "mcp.json")["mcpServers"]["teachify"]["command"] == "teachify"
    copilot = _json(fake_home / ".copilot" / "mcp-config.json")["mcpServers"]["teachify"]
    assert copilot["command"] == "teachify" and copilot["tools"] == ["*"]
    codex = (fake_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert '[mcp_servers.teachify]\ncommand = "teachify"' in codex
    assert _json(workdir / ".vscode" / "mcp.json")["servers"]["teachify"]["command"] == "teachify"
    assert (fake_home / ".claude" / "commands" / "teach.md").exists()


def test_install_is_idempotent(fake_home, workdir):
    installer.install()
    results = installer.install()
    assert all(status == "unchanged" for status in results.values())


def test_install_preserves_existing_config(fake_home, workdir):
    claude_json = fake_home / ".claude.json"
    claude_json.write_text(
        json.dumps({"mcpServers": {"other": {"command": "other-cmd"}}, "theme": "dark"}),
        encoding="utf-8",
    )
    codex_toml = fake_home / ".codex" / "config.toml"
    codex_toml.parent.mkdir(parents=True)
    codex_toml.write_text('[mcp_servers.other]\ncommand = "other-cmd"\n', encoding="utf-8")

    installer.install()

    data = _json(claude_json)
    assert data["mcpServers"]["other"]["command"] == "other-cmd"  # untouched
    assert data["mcpServers"]["teachify"]["command"] == "teachify"
    assert data["theme"] == "dark"  # untouched
    codex = codex_toml.read_text(encoding="utf-8")
    assert '[mcp_servers.other]\ncommand = "other-cmd"' in codex  # untouched
    assert "[mcp_servers.teachify]" in codex


def test_install_local_writes_project_configs(fake_home, workdir):
    results = installer.install(local=True)
    assert results["claude code (this project)"] == "added"
    assert "claude code" not in results
    assert _json(workdir / ".mcp.json")["mcpServers"]["teachify"]["command"] == "teachify"


def test_install_client_filter(fake_home, workdir):
    results = installer.install(clients=["codex"])
    assert list(results) == ["codex", "/teach slash command"]
    assert not (fake_home / ".claude.json").exists()


def test_install_custom_config(fake_home, workdir):
    custom = workdir / "windsurf.json"
    results = installer.install(clients=[], config=str(custom))
    assert "custom config" in next(iter(results))
    assert _json(custom)["mcpServers"]["teachify"]["command"] == "teachify"


def test_uninstall_removes_everything(fake_home, workdir):
    installer.install()
    results = installer.uninstall()
    assert results["claude code"] == "removed"
    assert results["codex"] == "removed"
    assert "teachify" not in _json(fake_home / ".claude.json").get("mcpServers", {})
    assert "teachify" not in (fake_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert not (fake_home / ".claude" / "commands" / "teach.md").exists()
    # second run is a clean no-op
    assert all(s == "unchanged" for s in installer.uninstall().values())


def test_uninstall_preserves_other_servers(fake_home, workdir):
    codex_toml = fake_home / ".codex" / "config.toml"
    codex_toml.parent.mkdir(parents=True)
    codex_toml.write_text('[mcp_servers.other]\ncommand = "other-cmd"\n', encoding="utf-8")
    installer.install()
    installer.uninstall()
    assert codex_toml.read_text(encoding="utf-8") == '[mcp_servers.other]\ncommand = "other-cmd"\n'
