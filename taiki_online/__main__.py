import argparse
import json
import sys
from pathlib import Path

__version__ = "0.1.0"

SETTINGS_BLOCK = {
    "type": "command",
    "command": "taiki-online",
    "padding": 0,
    "refreshInterval": 5000,
}


def cmd_setup():
    settings_path = Path.home() / ".claude" / "settings.json"
    data = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    data["statusLine"] = SETTINGS_BLOCK

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✓ statusLine configured in {settings_path}")
    print("  Restart Claude Code to see the status bar.")
    print(f'  Test: echo \'{{"session_id":"test"}}\' | taiki-online')


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--setup", action="store_true")
    args, _ = parser.parse_known_args()

    if args.version:
        print(f"taiki-online {__version__}")
        return

    if args.help:
        print(f"taiki-online {__version__} — Claude Code Status Line")
        print()
        print("Usage:")
        print("  echo '{\"session_id\":\"...\"}' | taiki-online")
        print()
        print("Options:")
        print("  --setup    Write statusLine config to ~/.claude/settings.json")
        print("  --version  Show version")
        print("  --help     Show this help")
        return

    if args.setup:
        cmd_setup()
        return

    from .core import run
    run()


if __name__ == "__main__":
    main()
