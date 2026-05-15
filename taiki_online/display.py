import os
import re
import shutil
import subprocess
import unicodedata


BAR_FILLED = "▓"
BAR_EMPTY  = "░"
BAR_LEN    = 10

NO_COLOR = os.environ.get("NO_COLOR") or os.environ.get("TAIKI_NO_COLOR")


class C:
    RESET   = "" if NO_COLOR else "\033[0m"
    BOLD    = "" if NO_COLOR else "\033[1m"
    # cool blue / purple palette
    MODEL   = "" if NO_COLOR else "\033[1;35m"   # bright magenta
    DIR     = "" if NO_COLOR else "\033[1;36m"   # bright cyan
    BRANCH  = "" if NO_COLOR else "\033[1;34m"   # bright blue
    MODIFIED = "" if NO_COLOR else "\033[1;33m"  # yellow for dirty
    COMMIT  = "" if NO_COLOR else "\033[38;5;245m"  # grey
    LINES_A = "" if NO_COLOR else "\033[1;32m"   # green
    LINES_D = "" if NO_COLOR else "\033[1;31m"   # red
    COST    = "" if NO_COLOR else "\033[1;37m"   # white
    BAR_F   = "" if NO_COLOR else "\033[1;34m"   # blue filled
    BAR_E   = "" if NO_COLOR else "\033[38;5;237m"  # dark gray empty
    LABEL   = "" if NO_COLOR else "\033[38;5;245m"  # gray label
    WARN    = "" if NO_COLOR else "\033[1;31m"   # red warning
    PCT_OK  = "" if NO_COLOR else "\033[1;37m"
    PCT_HI  = "" if NO_COLOR else "\033[1;31m"


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


def progress_bar(ratio, length=BAR_LEN):
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    return (
        C.BAR_F + BAR_FILLED * filled
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

    added   = ctx.get("lines_added", 0)
    removed = ctx.get("lines_removed", 0)
    if added or removed:
        parts.append(f"{C.LINES_A}+{added}{C.RESET}/{C.LINES_D}-{removed}{C.RESET}")

    cost = ctx.get("session_cost", 0)
    if cost > 0:
        parts.append(f"{C.COST}{fmt_cost(cost)}{C.RESET}")

    return f"  {C.LABEL}|{C.RESET}  ".join(parts)


def build_line2(ctx, width):
    used  = ctx.get("compact_tokens", 0)
    total = ctx.get("context_window_size", 200_000)
    ratio = used / total if total > 0 else 0

    pct_color = C.PCT_HI if ratio >= 0.8 else C.PCT_OK
    bar = progress_bar(ratio)
    label = f"{C.LABEL}Context{C.RESET}"
    pct   = f"{pct_color}{ratio*100:.0f}%{C.RESET}"
    nums  = f"{C.LABEL}{fmt_tokens(used)} / {fmt_tokens(total)}{C.RESET}"
    return f"  {label}  {bar}  {pct}  {nums}"


def build_line3(ctx, width):
    used_sec = ctx.get("session_duration_seconds") or 0
    total_sec = 5 * 3600
    ratio = min(1.0, used_sec / total_sec) if used_sec else 0

    pct_color = C.PCT_HI if ratio >= 0.8 else C.PCT_OK
    bar = progress_bar(ratio)
    label = f"{C.LABEL}Session{C.RESET}"
    pct   = f"{pct_color}{ratio*100:.0f}%{C.RESET}"

    elapsed_str = fmt_duration(used_sec) or "0m"
    dur = f"{C.LABEL}{elapsed_str} / 5h{C.RESET}"
    return f"  {label}  {bar}  {pct}  {dur}"


def render(ctx):
    width = get_terminal_width()
    lines = [
        build_line1(ctx, width),
        build_line2(ctx, width),
        build_line3(ctx, width),
    ]
    return "\n".join(f"\033[0m\033[1;97m{ln}\033[0m" for ln in lines)
