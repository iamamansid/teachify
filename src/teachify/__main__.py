"""Command-line entry point.

- `teachify`            run the MCP server over stdio (default)
- `teachify install`    register Teachify in your AI clients — no manual config
- `teachify uninstall`  remove it again
- `teachify --version`  print the version
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="teachify",
        description="Teach Mode for any LLM — the AI guides, you type, you learn.",
    )
    parser.add_argument("--version", "-v", action="store_true", help="Print the version.")
    sub = parser.add_subparsers(dest="command")

    p_install = sub.add_parser(
        "install", help="Register Teachify in your AI clients (no manual config editing)."
    )
    p_install.add_argument(
        "--local",
        action="store_true",
        help="Write project configs (./.mcp.json, ./.vscode/mcp.json) instead of user-global ones.",
    )
    p_install.add_argument(
        "--client",
        action="append",
        choices=["claude", "cursor", "vscode", "codex", "copilot"],
        dest="clients",
        help="Only set up these clients (repeatable). Default: all five.",
    )
    p_install.add_argument(
        "--config",
        metavar="PATH",
        help="Also register in any other agent's JSON config file (escape hatch).",
    )
    p_install.add_argument(
        "--key",
        default="mcpServers",
        help="Top-level key for --config (default: mcpServers).",
    )
    sub.add_parser("uninstall", help="Remove Teachify from AI client configs.")

    args = parser.parse_args()

    if args.version:
        from . import __version__

        print(f"teachify {__version__}")
        return

    if args.command == "install":
        from .installer import install

        for label, status in install(
            local=args.local, clients=args.clients, config=args.config, config_key=args.key
        ).items():
            print(f"  {label}: {status}")
        print("\nDone — restart your agent client, then type: /teach <what you want to learn>")
        return

    if args.command == "uninstall":
        from .installer import uninstall

        for label, status in uninstall().items():
            print(f"  {label}: {status}")
        return

    from .server import mcp

    mcp.run()


if __name__ == "__main__":
    main()
