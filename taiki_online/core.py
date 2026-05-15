import json
import os
import sys

from .git import get_git_info, get_last_commit_elapsed
from .session import get_session_duration, get_session_tokens
from .display import render


def run():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.stdout.write("[taiki-online] invalid JSON\n")
        sys.stdout.flush()
        return

    cost_data    = data.get("cost", {})
    ctx_data     = data.get("context_window", {})
    workspace    = data.get("workspace", {})
    cwd          = workspace.get("current_dir") or data.get("cwd", ".")
    session_id   = data.get("session_id") or data.get("sessionId")
    transcript   = data.get("transcript_path")

    model = (data.get("model") or {}).get("display_name", "Unknown")
    current_dir = os.path.basename(cwd) if cwd else "."

    total_cost      = cost_data.get("total_cost_usd", 0)
    lines_added     = cost_data.get("total_lines_added", 0)
    lines_removed   = cost_data.get("total_lines_removed", 0)
    api_duration_ms = cost_data.get("total_duration_ms")

    input_tokens = ctx_data.get("total_input_tokens", 0)
    context_size = ctx_data.get("context_window_size", 200_000)

    # Cache hit tokens (CC v2.x — context_window.current_usage)
    current_usage    = ctx_data.get("current_usage") or {}
    cache_read_tokens = current_usage.get("cache_read_input_tokens", 0)

    # Weekly rate limit (CC v2.1.80+)
    rate_limits  = data.get("rate_limits", {})
    seven_day    = rate_limits.get("seven_day", {})
    weekly_util  = seven_day.get("used_percentage") if seven_day else None
    weekly_resets = seven_day.get("resets_at") if seven_day else None

    git_branch, modified_files, _ = get_git_info(cwd)
    last_commit = get_last_commit_elapsed(cwd)

    duration_sec = get_session_duration(session_id, transcript, api_duration_ms)

    # $/hr burn rate — only meaningful after at least 2 minutes of session
    burn_rate = None
    if duration_sec and duration_sec >= 120 and total_cost > 0:
        burn_rate = (total_cost / duration_sec) * 3600

    ctx = {
        "model":                    model,
        "current_dir":              current_dir,
        "git_branch":               git_branch,
        "modified_files":           modified_files,
        "last_commit_elapsed":      last_commit,
        "session_cost":             total_cost,
        "burn_rate_per_hour":       burn_rate,
        "compact_tokens":           input_tokens,
        "context_window_size":      context_size,
        "cache_read_tokens":        cache_read_tokens,
        "session_duration_seconds": duration_sec,
        "weekly_utilization":       weekly_util,
        "weekly_resets_at":         weekly_resets,
    }

    sys.stdout.write(render(ctx) + "\n")
    sys.stdout.flush()
