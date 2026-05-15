# taiki-online

A clean, minimal status line for [Claude Code](https://claude.ai/code).

```
  [Sonnet4.6]  |  📁 Gugen  |  🌿 feat/auth  M2  |  ⏱ 2h  |  +12/-3  |  $0.42
  Context  ▓▓▓▓▓▓▓░░░  67%  134.0K / 200.0K
  Session  ▓▓▓░░░░░░░  28%  1h24m / 5h
```

## Features

- **Model** · **directory** · **git branch** · **lines changed** · **session cost** on one line
- **⏱ time since last commit** — helps you notice when you forgot to commit
- Context window usage bar (`▓░` style)
- Session window progress (5-hour block)
- Cool blue/purple color palette, pipe-separated layout

## Install

```bash
pip install taiki-online
# or
pipx install taiki-online
```

## Setup

```bash
taiki-online --setup
```

This writes the `statusLine` block to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "taiki-online",
    "padding": 0,
    "refreshInterval": 5000
  }
}
```

Restart Claude Code to activate.

## Manual test

```bash
echo '{"session_id":"test","model":{"display_name":"claude-sonnet-4-6"},"cost":{"total_cost_usd":0.42,"total_lines_added":12,"total_lines_removed":3},"context_window":{"total_input_tokens":134000,"context_window_size":200000},"workspace":{"current_dir":"."}}' | taiki-online
```

## Environment variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disable ANSI colors |
| `TAIKI_NO_COLOR` | Same as above |

## License

MIT — [taiki200504](https://github.com/taiki200504)
