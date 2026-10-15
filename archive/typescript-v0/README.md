# Archived: TypeScript implementation (v0.x)

This folder preserves the original TypeScript/Node implementation of Teachify
(v0.0–v0.1), moved here when the canonical distribution became the Python
package (`pip install teachify`, v0.2.0+). Nothing in `archive/` is part of
the Python build.

Contents:
- `src/server.ts` — the original MCP server (Node, `@modelcontextprotocol/sdk`)
- `src/engine/` — the original teach engine (sessions, tasks, verifier, hints, plan, teach-mode) + tests
- `src/prompts/teach-mode.md` — original Teach Mode system prompt
- `src/tasks/*.json` — original demo task definitions
- `scripts/copy-tasks.js` — original build helper
- `vscode-extension/` — thin VS Code client. It spawned the **Node** server
  (`../dist/server.js`); it is not wired to the Python server. Kept for reference.
- `package.json`, `package-lock.json`, `tsconfig.json` — original Node build files

Behavior was ported 1:1 to Python (`src/teachify/` at the repo root). If you
need to compare behavior, the TypeScript tests are the reference.
