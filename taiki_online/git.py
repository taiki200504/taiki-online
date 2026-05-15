import subprocess
import time


def get_git_info(cwd="."):
    branch = None
    modified = 0
    untracked = 0
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2, cwd=cwd,
        )
        if r.returncode == 0:
            branch = r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None, 0, 0

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=2, cwd=cwd,
        )
        for line in r.stdout.splitlines():
            if line.startswith("??"):
                untracked += 1
            elif line.strip():
                modified += 1
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return branch, modified, untracked


def get_last_commit_elapsed(cwd="."):
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=2, cwd=cwd,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        elapsed = int(time.time()) - int(r.stdout.strip())
        if elapsed < 3600:
            m = elapsed // 60
            return f"⏱ {m}m" if m > 0 else "⏱ <1m"
        elif elapsed < 86400:
            return f"⏱ {elapsed // 3600}h"
        else:
            return f"⏱ {elapsed // 86400}d"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        return None
