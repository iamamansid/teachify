"""`teachify install` — one-command setup for every major agent.

Registers the Teachify MCP server in each detected client's config file so the
user never has to hand-edit JSON/TOML, and installs the /teach slash command
for Claude Code. Everything is idempotent: running it twice changes nothing
the second time.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

SERVER_NAME = "teachify"
SERVER_ENTRY = {"command": "teachify", "args": []}
# Copilot CLI wants an explicit tools allow-list; harmless elsewhere.
COPILOT_ENTRY = {"command": "teachify", "args": [], "tools": ["*"]}
CODEX_HEADER = "[mcp_servers.teachify]"
CODEX_BLOCK = '[mcp_servers.teachify]\ncommand = "teachify"\nargs = []\n'


# ---------------------------------------------------------------- JSON helpers

def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _upsert_json(path: Path, key: str, entry: dict) -> str:
    """Insert/update the teachify entry under `key`. Returns added/updated/unchanged."""
    data = _read_json(path)
    servers = data.get(key)
    if not isinstance(servers, dict):
        servers = {}
        data[key] = servers
    if servers.get(SERVER_NAME) == entry:
        return "unchanged"
    action = "updated" if SERVER_NAME in servers else "added"
    servers[SERVER_NAME] = dict(entry)
    _write_json(path, data)
    return action


def _remove_json(path: Path, key: str) -> str:
    data = _read_json(path)
    servers = data.get(key)
    if isinstance(servers, dict) and SERVER_NAME in servers:
        del servers[SERVER_NAME]
        _write_json(path, data)
        return "removed"
    return "unchanged"


# ---------------------------------------------------------------- TOML helpers (Codex)

def _upsert_codex_toml(path: Path) -> str:
    """Insert/replace the [mcp_servers.teachify] table. Returns added/updated/unchanged."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i, found, action = 0, False, "added"
    while i < len(lines):
        if lines[i].strip() == CODEX_HEADER:
            found = True
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("["):
                j += 1
            if "".join(lines[i:j]).strip() == CODEX_BLOCK.strip():
                return "unchanged"
            out.append(CODEX_BLOCK)
            i = j
            action = "updated"
        else:
            out.append(lines[i])
            i += 1
    if not found:
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        if out:
            out.append("\n")
        out.append(CODEX_BLOCK)
    new_text = "".join(out)
    if new_text != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text, encoding="utf-8")
    return action


def _remove_codex_toml(path: Path) -> str:
    if not path.exists():
        return "unchanged"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    i, removed = 0, False
    while i < len(lines):
        if lines[i].strip() == CODEX_HEADER:
            removed = True
            # also drop the single blank line our installer inserts before an appended block
            if out and out[-1].strip() == "":
                out.pop()
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("["):
                i += 1
        else:
            out.append(lines[i])
            i += 1
    if removed:
        path.write_text("".join(out), encoding="utf-8")
        return "removed"
    return "unchanged"


# ---------------------------------------------------------------- slash command

def _install_slash_command() -> str:
    src = resources.files("teachify") / "commands" / "teach.md"
    text = src.read_text(encoding="utf-8")
    target = Path.home() / ".claude" / "commands" / "teach.md"
    if target.exists() and target.read_text(encoding="utf-8") == text:
        return "unchanged"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return "added"


# ---------------------------------------------------------------- public API

def _client_entry(client: str) -> dict:
    return dict(COPILOT_ENTRY) if client == "copilot" else dict(SERVER_ENTRY)


def install(
    local: bool = False,
    clients: list[str] | None = None,
    config: str | None = None,
    config_key: str = "mcpServers",
) -> dict[str, str]:
    """Register Teachify everywhere requested. Returns {label: status}.

    - local=True writes project configs (./.mcp.json, ./.vscode/mcp.json)
      instead of user-global ones.
    - clients filters to a subset of {"claude","cursor","vscode","codex","copilot"}.
    - config points at any other agent's JSON config file (escape hatch for
      agents not listed above); config_key is its top-level key.
    """
    want = set(clients) if clients is not None else {"claude", "cursor", "vscode", "codex", "copilot"}
    results: dict[str, str] = {}

    if "claude" in want:
        if local:
            results["claude code (this project)"] = _upsert_json(
                Path.cwd() / ".mcp.json", "mcpServers", _client_entry("claude")
            )
        else:
            results["claude code"] = _upsert_json(
                Path.home() / ".claude.json", "mcpServers", _client_entry("claude")
            )
    if "cursor" in want:
        results["cursor"] = _upsert_json(
            Path.home() / ".cursor" / "mcp.json", "mcpServers", _client_entry("cursor")
        )
    if "copilot" in want:
        results["copilot cli"] = _upsert_json(
            Path.home() / ".copilot" / "mcp-config.json",
            "mcpServers",
            _client_entry("copilot"),
        )
    if "codex" in want:
        results["codex"] = _upsert_codex_toml(Path.home() / ".codex" / "config.toml")
    if "vscode" in want:
        # VS Code reads workspace config; its key is "servers", not "mcpServers".
        results["vscode (this project)"] = _upsert_json(
            Path.cwd() / ".vscode" / "mcp.json", "servers", _client_entry("vscode")
        )
    if config:
        results[f"custom config ({config})"] = _upsert_json(
            Path(config).expanduser(), config_key, dict(SERVER_ENTRY)
        )

    results["/teach slash command"] = _install_slash_command()
    return results


def uninstall() -> dict[str, str]:
    """Remove Teachify from every known config. Returns {label: status}."""
    results = {
        "claude code": _remove_json(Path.home() / ".claude.json", "mcpServers"),
        "claude code (this project)": _remove_json(Path.cwd() / ".mcp.json", "mcpServers"),
        "cursor": _remove_json(Path.home() / ".cursor" / "mcp.json", "mcpServers"),
        "copilot cli": _remove_json(
            Path.home() / ".copilot" / "mcp-config.json", "mcpServers"
        ),
        "codex": _remove_codex_toml(Path.home() / ".codex" / "config.toml"),
        "vscode (this project)": _remove_json(Path.cwd() / ".vscode" / "mcp.json", "servers"),
    }
    target = Path.home() / ".claude" / "commands" / "teach.md"
    if target.exists():
        target.unlink()
        results["/teach slash command"] = "removed"
    else:
        results["/teach slash command"] = "unchanged"
    return results
