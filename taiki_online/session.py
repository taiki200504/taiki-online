import json
import os
from datetime import datetime, timezone
from pathlib import Path


def find_transcript(session_id):
    if not session_id:
        return None
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return None
    for project_dir in base.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


def get_session_tokens(session_id, transcript_path=None):
    if transcript_path:
        tf = Path(transcript_path)
    else:
        tf = find_transcript(session_id)
    if not tf or not tf.exists():
        return 0, None

    total = 0
    start_time = None
    try:
        with open(tf, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                ts = entry.get("timestamp")
                if ts and start_time is None:
                    try:
                        start_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                usage = entry.get("message", {}).get("usage", {})
                if usage:
                    total += usage.get("input_tokens", 0)
                    total += usage.get("output_tokens", 0)
    except (OSError, IOError):
        pass

    return total, start_time


def get_session_duration(session_id, transcript_path=None, api_duration_ms=None):
    if api_duration_ms is not None and api_duration_ms > 0:
        return api_duration_ms / 1000

    _, start_time = get_session_tokens(session_id, transcript_path)
    if start_time is None:
        return None

    now = datetime.now(tz=timezone.utc)
    return (now - start_time).total_seconds()
