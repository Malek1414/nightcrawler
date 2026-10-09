#!/usr/bin/env python3
"""Mutation eval for the verify gate: how many ways of faking a citation does it catch?

Builds a small, correct report with three sources served from a local HTTP server,
then applies one mutation at a time and checks whether sources.py rejects it.
Deterministic, no API keys, no external network.

Runs every mutation twice: plain `verify` and `verify --numbers`.
Exit code 1 if `--numbers` misses any mutation (used as a CI regression check).

  python3 evals/gate_mutations.py          # table
  python3 evals/gate_mutations.py --json   # machine-readable
"""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "research-agent", "references", "sources.py")

PAGES = {
    "grant.html": "<p>The fellowship pays 630 euros per month for up to twelve months.</p>",
    "deadline.html": "<p>Applications close on 1 October 2026 at noon CET.</p>",
    "eligibility.html": "<p>Applicants must be between 16 and 21 years old.</p>",
}
QUOTES = {1: "pays 630 euros per month", 2: "close on 1 October 2026", 3: "between 16 and 21 years old"}
REPORT = ("The fellowship pays 630 euros a month [s01]. "
          "The deadline is 1 October 2026 [s02]. Applicants are 16 to 21 [s03].\n")


FLAGS = []


def cli(ledger, *args):
    if args and args[0] == "verify":
        args = (*args, *FLAGS)
    return subprocess.run([sys.executable, CLI, "--ledger", ledger, *args], capture_output=True, text=True)


def build(work, base):
    ledger = os.path.join(work, "sources.json")
    for i, name in enumerate(PAGES, 1):
        cli(ledger, "add", f"{base}/{name}")
        page = os.path.join(work, f"p{i}.txt")
        with open(page, "w") as f:
            f.write(PAGES[name])
        r = cli(ledger, "quote", str(i), "--from", page, "--text", QUOTES[i])
        assert r.returncode == 0, r.stderr
    return ledger


def write(work, text):
    path = os.path.join(work, "draft.md")
    with open(path, "w") as f:
        f.write(text)
    return path


# Each mutation returns True if the gate (or the quote step) rejected the fake.
def m_fabricated_citation(work, ledger, site):
    return cli(ledger, "verify", write(work, REPORT + "It is the largest in Europe [s04].\n")).returncode != 0


def m_invented_quote(work, ledger, site):
    return cli(ledger, "quote", "1", "--from", os.path.join(work, "p1.txt"),
               "--text", "pays 900 euros per month").returncode != 0


def m_citation_without_quote(work, ledger, site):
    cli(ledger, "add", "https://example.org/unread")
    return cli(ledger, "verify", write(work, REPORT + "Most winners are engineers [s04].\n")).returncode != 0


def m_swapped_citation(work, ledger, site):
    swapped = REPORT.replace("[s01]", "[sXX]").replace("[s02]", "[s01]").replace("[sXX]", "[s02]")
    return cli(ledger, "verify", write(work, swapped)).returncode != 0


def m_claim_changed(work, ledger, site):
    return cli(ledger, "verify", write(work, REPORT.replace("630", "900", 1))).returncode != 0


def m_page_changed_later(work, ledger, site):
    with open(os.path.join(site, "grant.html"), "w") as f:
        f.write("<p>The fellowship has been discontinued.</p>")
    return cli(ledger, "verify", write(work, REPORT), "--check-urls").returncode != 0


def m_page_gone(work, ledger, site):
    os.remove(os.path.join(site, "deadline.html"))
    return cli(ledger, "verify", write(work, REPORT), "--check-urls").returncode != 0


MUTATIONS = [
    ("fabricated citation [s04] with no source", m_fabricated_citation),
    ("quote that is not on the page", m_invented_quote),
    ("source added but never quoted", m_citation_without_quote),
    ("source page changed after quoting (--check-urls)", m_page_changed_later),
    ("source page removed (--check-urls)", m_page_gone),
    ("two citations swapped", m_swapped_citation),
    ("claim changed, citation kept", m_claim_changed),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run():
    results = []
    for label, fn in MUTATIONS:
        work, site = tempfile.mkdtemp(), tempfile.mkdtemp()
        for name, html in PAGES.items():
            with open(os.path.join(site, name), "w") as f:
                f.write(html)
        handler = functools.partial(Quiet, directory=site)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            ledger = build(work, f"http://127.0.0.1:{srv.server_port}")
            baseline_ok = cli(ledger, "verify", write(work, REPORT), "--check-urls").returncode == 0
            assert baseline_ok, "unmutated report must pass the gate"
            results.append({"mutation": label, "caught": fn(work, ledger, site)})
        finally:
            srv.shutdown()
            shutil.rmtree(work)
            shutil.rmtree(site)
    return results


if __name__ == "__main__":
    modes = {"verify": [], "verify --numbers": ["--numbers"]}
    table = {}
    for mode, flags in modes.items():
        FLAGS[:] = flags
        table[mode] = run()
    if "--json" in sys.argv:
        print(json.dumps({m: {"caught": sum(r["caught"] for r in res), "total": len(res), "results": res}
                          for m, res in table.items()}, indent=2))
    else:
        print("| Mutation | " + " | ".join(f"`{m}`" for m in modes) + " |")
        print("|---|" + "---|" * len(modes))
        for i, (label, _) in enumerate(MUTATIONS):
            print(f"| {label} | " + " | ".join("caught" if table[m][i]["caught"] else "missed" for m in modes) + " |")
        print("| **total** | " + " | ".join(f"**{sum(r['caught'] for r in table[m])}/{len(MUTATIONS)}**" for m in modes) + " |")
    sys.exit(0 if all(r["caught"] for r in table["verify --numbers"]) else 1)
