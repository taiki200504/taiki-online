import os
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime, timedelta, timezone


BAR_FILLED = "▓"
BAR_EMPTY  = "░"
BAR_LEN    = 10

NO_COLOR = os.environ.get("NO_COLOR") or os.environ.get("TAIKI_NO_COLOR")


class C:
    RESET   = "" if NO_COLOR else "\033[0m"
    BOLD    = "" if NO_COLOR else "\033[1m"
    # vivid palette — high contrast on dark terminals
    MODEL    = "" if NO_COLOR else "\033[38;5;213m"  # hot pink
    DIR      = "" if NO_COLOR else "\033[38;5;123m"  # sky blue
    BRANCH   = "" if NO_COLOR else "\033[38;5;118m"  # lime green
    MODIFIED = "" if NO_COLOR else "\033[1;93m"       # bright yellow
    COMMIT   = "" if NO_COLOR else "\033[38;5;250m"  # light gray
    COST     = "" if NO_COLOR else "\033[38;5;220m"  # gold
    BURN     = "" if NO_COLOR else "\033[38;5;215m"  # peach (burn rate)
    CACHE_HI = "" if NO_COLOR else "\033[38;5;118m"  # lime green (cache good)
    CACHE_LO = "" if NO_COLOR else "\033[38;5;203m"  # coral (cache low)
    BAR_E    = "" if NO_COLOR else "\033[38;5;237m"  # dark gray empty
    # context bar zone colors (dumb-zone theory)
    ZONE_OK  = "" if NO_COLOR else "\033[38;5;118m"  # lime green  0–50%
    ZONE_MID = "" if NO_COLOR else "\033[1;93m"       # yellow      50–75%
    ZONE_HI  = "" if NO_COLOR else "\033[38;5;214m"  # orange      75–90%
    ZONE_MAX = "" if NO_COLOR else "\033[38;5;203m"  # coral red   90%+
    LABEL    = "" if NO_COLOR else "\033[38;5;245m"  # gray label
    WARN     = "" if NO_COLOR else "\033[1;31m"       # red warning
    PCT_OK   = "" if NO_COLOR else "\033[1;97m"       # bright white
    PCT_HI   = "" if NO_COLOR else "\033[38;5;203m"  # coral red (danger)


def _zone_color(ratio):
    if ratio >= 0.90:
        return C.ZONE_MAX
    if ratio >= 0.75:
        return C.ZONE_HI
    if ratio >= 0.50:
        return C.ZONE_MID
    return C.ZONE_OK


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def display_width(text):
    clean = strip_ansi(text)
    w = 0
    for ch in clean:
        ea = unicodedata.east_asian_width(ch)
        w += 2 if ea in ("W", "F") else 1
    return w


def get_terminal_width():
    try:
        if "TMUX" in os.environ:
            pane = os.environ.get("TMUX_PANE", "")
            cmd = ["tmux", "display-message", "-p", "#{pane_width}"]
            if pane:
                cmd = ["tmux", "display-message", "-t", pane, "-p", "#{pane_width}"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            if r.returncode == 0 and r.stdout.strip().isdigit():
                return max(10, int(r.stdout.strip()) - 1)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    try:
        if os.isatty(1):
            return max(10, shutil.get_terminal_size().columns - 1)
    except (OSError, AttributeError):
        pass
    return 100


def progress_bar(ratio, length=BAR_LEN, fill_color=None):
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    color = fill_color or C.ZONE_OK
    return (
        color + BAR_FILLED * filled
        + C.BAR_E + BAR_EMPTY * (length - filled)
        + C.RESET
    )


def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def fmt_cost(usd):
    if usd >= 100:
        return f"${usd:.0f}"
    if usd >= 10:
        return f"${usd:.1f}"
    return f"${usd:.2f}"


def fmt_duration(seconds):
    if seconds is None or seconds <= 0:
        return None
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    if h > 0:
        return f"{h}h{m:02d}m"
    return f"{m}m"


def shorten_model(name):
    name = name or "Unknown"
    replacements = [
        ("claude-opus-4-", "Opus4."),
        ("claude-sonnet-4-", "Sonnet4."),
        ("claude-haiku-4-", "Haiku4."),
        ("claude-opus-",    "Opus"),
        ("claude-sonnet-",  "Sonnet"),
        ("claude-haiku-",   "Haiku"),
        ("claude-",         "Claude"),
    ]
    for prefix, short in replacements:
        if name.lower().startswith(prefix):
            return short + name[len(prefix):]
    return name


def build_line1(ctx, width):
    parts = []

    model = shorten_model(ctx.get("model", "Unknown"))
    parts.append(f"{C.MODEL}[{model}]{C.RESET}")

    cwd = ctx.get("current_dir", ".")
    parts.append(f"{C.DIR}📁 {cwd}{C.RESET}")

    branch = ctx.get("git_branch")
    if branch:
        b = f"{C.BRANCH}🌿 {branch}{C.RESET}"
        modified = ctx.get("modified_files", 0)
        if modified:
            b += f" {C.MODIFIED}M{modified}{C.RESET}"
        parts.append(b)

    elapsed = ctx.get("last_commit_elapsed")
    if elapsed:
        parts.append(f"{C.COMMIT}{elapsed}{C.RESET}")

    cost = ctx.get("session_cost", 0)
    burn = ctx.get("burn_rate_per_hour")
    if cost > 0:
        cost_str = f"{C.COST}{fmt_cost(cost)}{C.RESET}"
        if burn and burn > 0:
            cost_str += f" {C.BURN}{fmt_cost(burn)}/h{C.RESET}"
        parts.append(cost_str)

    return f"  {C.LABEL}|{C.RESET}  ".join(parts)


def build_line2(ctx, width):
    used  = ctx.get("compact_tokens", 0)
    total = ctx.get("context_window_size", 200_000)
    ratio = used / total if total > 0 else 0

    zone_color = _zone_color(ratio)
    pct_color  = C.PCT_HI if ratio >= 0.75 else C.PCT_OK
    bar   = progress_bar(ratio, fill_color=zone_color)
    label = f"{C.LABEL}Context{C.RESET}"
    pct   = f"{pct_color}{ratio*100:.0f}%{C.RESET}"
    nums  = f"{C.LABEL}{fmt_tokens(used)} / {fmt_tokens(total)}{C.RESET}"

    # Cache hit ratio
    cache_read  = ctx.get("cache_read_tokens", 0)
    cache_ratio = cache_read / used if used > 0 else 0
    cache_str = ""
    if cache_read > 0:
        cache_color = C.CACHE_HI if cache_ratio >= 0.5 else C.CACHE_LO
        cache_str = f"  {C.LABEL}💾{C.RESET}{cache_color}{cache_ratio*100:.0f}%{C.RESET}"

    return f"  {label}  {bar}  {pct}  {nums}{cache_str}"


def build_line3(ctx, width):
    used_sec = ctx.get("session_duration_seconds") or 0
    total_sec = 5 * 3600
    ratio = min(1.0, used_sec / total_sec) if used_sec else 0

    pct_color = C.PCT_HI if ratio >= 0.8 else C.PCT_OK
    bar = progress_bar(ratio, fill_color=C.ZONE_OK)
    label = f"{C.LABEL}Session{C.RESET}"
    pct   = f"{pct_color}{ratio*100:.0f}%{C.RESET}"

    elapsed_str = fmt_duration(used_sec) or "0m"
    dur = f"{C.LABEL}{elapsed_str} / 5h{C.RESET}"
    return f"  {label}  {bar}  {pct}  {dur}"


def build_line4_weekly(ctx, width):
    util      = ctx.get("weekly_utilization")
    resets_at = ctx.get("weekly_resets_at")

    if util is None and resets_at is None:
        return None

    ratio = (util / 100.0) if util is not None else 0.0
    ratio = max(0.0, min(1.0, ratio))

    zone_color = _zone_color(ratio)
    pct_color  = C.PCT_HI if ratio >= 0.75 else C.PCT_OK
    bar   = progress_bar(ratio, fill_color=zone_color)
    label = f"{C.LABEL}Weekly {C.RESET}"
    pct   = f"{pct_color}{ratio*100:.0f}%{C.RESET}"

    remaining_str = None
    if resets_at is not None:
        try:
            if isinstance(resets_at, (int, float)):
                resets_dt = datetime.fromtimestamp(resets_at, tz=timezone.utc)
            else:
                resets_dt = datetime.fromisoformat(str(resets_at).replace("Z", "+00:00"))
            remaining = max(0, (resets_dt - datetime.now(tz=timezone.utc)).total_seconds())
            if remaining < 3600:
                remaining_str = f"{int(remaining // 60)}m left"
            elif remaining < 86400:
                h = int(remaining // 3600)
                m = int((remaining % 3600) // 60)
                remaining_str = f"{h}h{m:02d}m left"
            else:
                d = int(remaining // 86400)
                h = int((remaining % 86400) // 3600)
                remaining_str = f"{d}d{h:02d}h left"
        except (ValueError, TypeError, OSError):
            pass

    parts = [f"  {label} {bar}  {pct}"]
    if remaining_str:
        parts.append(f"  {C.LABEL}{remaining_str}{C.RESET}")
    return "".join(parts)


def render(ctx):
    width = get_terminal_width()
    lines = [
        build_line1(ctx, width),
        build_line2(ctx, width),
        build_line3(ctx, width),
    ]
    weekly = build_line4_weekly(ctx, width)
    if weekly:
        lines.append(weekly)
    return "\n".join(f"\033[0m\033[1;97m{ln}\033[0m" for ln in lines)
