#!/usr/bin/env python3
"""Create the working folder for one /nightcrawler run and print its paths as JSON.

    new_run.py "find polymarket agents with real returns"
    -> {"slug": "polymarket-agents-real-returns-2026-10-10", "run_dir": ..., "seen": ..., "report": ..., "profile": ...}

Runs land in $NIGHTCRAWLER_RUNS, else ./runs next to profile.toml if the repo
is the working directory, else ~/nightcrawler-runs. A taken slug gets -2, -3, ...
so a rerun never overwrites an earlier one. Stdlib only.
"""
import datetime
import json
import os
import re
import sys

STOP = {
    "a", "an", "and", "the", "of", "for", "to", "in", "on", "with", "that", "have", "has",
    "find", "search", "research", "look", "up", "me", "my", "some", "good", "best", "all",
    "please", "can", "you", "go", "about", "what", "which", "who", "is", "are", "do", "on",
}


def slugify(task, max_words=6):
    words = re.findall(r"[a-z0-9]+", task.lower())
    kept = [w for w in words if w not in STOP] or words or ["run"]
    return "-".join(kept[:max_words])[:60].strip("-") or "run"


def runs_root(cwd):
    env = os.environ.get("NIGHTCRAWLER_RUNS")
    if env:
        return os.path.expanduser(env)
    if os.path.exists(os.path.join(cwd, "profile.toml")):
        return os.path.join(cwd, "runs")
    return os.path.expanduser("~/nightcrawler-runs")


def find_profile(cwd, root):
    candidates = [os.environ.get("NIGHTCRAWLER_PROFILE"),
                  os.path.join(cwd, "profile.toml"),
                  os.path.join(os.path.dirname(os.path.abspath(root)), "profile.toml")]
    for c in candidates:
        if c and os.path.isfile(os.path.expanduser(c)):
            return os.path.abspath(os.path.expanduser(c))
    return None


def new_run(task, cwd=None, today=None):
    cwd = cwd or os.getcwd()
    root = runs_root(cwd)
    day = (today or datetime.date.today()).isoformat()
    base = f"{slugify(task)}-{day}"
    slug, n = base, 2
    while os.path.exists(os.path.join(root, slug)) or os.path.exists(os.path.join(root, slug + ".md")):
        slug, n = f"{base}-{n}", n + 1
    run_dir = os.path.join(root, slug)
    os.makedirs(os.path.join(run_dir, "pages"))
    seen = os.path.join(run_dir, "seen.txt")
    open(seen, "a").close()
    with open(os.path.join(run_dir, "task.txt"), "w", encoding="utf-8") as f:
        f.write(task.strip() + "\n")
    return {
        "slug": slug,
        "run_dir": os.path.abspath(run_dir),
        "seen": os.path.abspath(seen),
        "report": os.path.abspath(os.path.join(root, slug + ".md")),
        "profile": find_profile(cwd, root),
    }


def main(argv):
    task = " ".join(argv).strip()
    if not task:
        print('usage: new_run.py "<task>"', file=sys.stderr)
        return 2
    print(json.dumps(new_run(task), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
