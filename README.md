# taiki-online

A clean status line for [Claude Code](https://claude.ai/code) with cache diagnostics, burn rate, and smart color zones.

```
  [Sonnet4.6]  |  📁 Gugen  |  🌿 feat/auth  M2  |  ⏱ 2h  |  $0.42 $0.30/h
  Context  ▓▓▓▓▓▓▓░░░  67%  134.0K / 200.0K  💾73%
  Session  ▓▓▓░░░░░░░  28%  1h24m / 5h
  Weekly   ▓▓▓▓▓▓░░░░  64%  4d10h left
```

## Features

| Line | Content |
|---|---|
| **Line 1** | Model · directory · git branch · ⏱ time since last commit · session cost · **$/hr burn rate** |
| **Line 2** | Context window bar + % + tokens · **💾 cache hit ratio** |
| **Line 3** | 5-hour session window progress |
| **Line 4** | 7-day rate limit usage + reset countdown *(hidden when API data unavailable)* |

### Context bar color zones

Inspired by [claudeline](https://github.com/fredrikaverpil/claudeline)'s dumb-zone theory:

| Range | Color | Zone |
|---|---|---|
| 0–50% | 🟢 Lime green | Smart zone |
| 50–75% | 🟡 Yellow | Dumb zone |
| 75–90% | 🟠 Orange | Danger |
| 90%+ | 🔴 Coral red | Near compaction |

### Cache hit ratio (`💾`)

`cache_read_input_tokens / total_input_tokens` — green ≥ 50%, red < 50%.  
High cache hit = up to **10× less rate-limit** quota consumed on Pro/Max plans.

### $/hr burn rate

Shown next to session cost after ≥ 2 minutes. Helps you spot expensive sessions early.

## Install

```bash
pip install git+https://github.com/taiki200504/taiki-online.git
```

> PyPI release coming soon. For now, install directly from GitHub.

## Setup

```bash
taiki-online --setup
```

Writes the `statusLine` block to `~/.claude/settings.json`:

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
echo '{
  "session_id": "test",
  "model": {"display_name": "claude-sonnet-4-6"},
  "cost": {"total_cost_usd": 0.42, "total_duration_ms": 5040000},
  "context_window": {
    "total_input_tokens": 134000,
    "context_window_size": 200000,
    "current_usage": {"cache_read_input_tokens": 98000}
  },
  "workspace": {"current_dir": "."},
  "rate_limits": {
    "seven_day": {"used_percentage": 64, "resets_at": "2026-05-20T09:00:00+00:00"}
  }
}' | taiki-online
```

## Environment variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disable ANSI colors |
| `TAIKI_NO_COLOR` | Same as above |

## Requirements

- Python 3.9+
- Claude Code (any version; Line 4 requires CC v2.1.80+ for rate limit data)

## License

MIT — [taiki200504](https://github.com/taiki200504)
