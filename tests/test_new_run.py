"""Tests for the /nightcrawler run-folder helper (scripts/new_run.py)."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import new_run  # noqa: E402

CLI = os.path.join(os.path.dirname(__file__), "..", "scripts", "new_run.py")
DAY = datetime.date(2026, 10, 10)


class NewRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug_drops_filler_words(self):
        self.assertEqual(new_run.slugify("Find the best Polymarket agents with excellent returns!"),
                         "polymarket-agents-excellent-returns")
        self.assertEqual(new_run.slugify("???"), "run")

    def test_creates_folder_and_never_overwrites(self):
        with mock.patch.dict(os.environ, {"NIGHTCRAWLER_RUNS": self.d}):
            a = new_run.new_run("polymarket agents", cwd=self.d, today=DAY)
            b = new_run.new_run("polymarket agents", cwd=self.d, today=DAY)
        self.assertEqual(a["slug"], "polymarket-agents-2026-10-10")
        self.assertEqual(b["slug"], "polymarket-agents-2026-10-10-2")
        self.assertTrue(os.path.isfile(a["seen"]))
        self.assertTrue(os.path.isdir(os.path.join(a["run_dir"], "pages")))
        self.assertEqual(a["report"], os.path.join(self.d, "polymarket-agents-2026-10-10.md"))

    def test_repo_cwd_uses_runs_and_finds_profile(self):
        open(os.path.join(self.d, "profile.toml"), "w").close()
        env = {k: v for k, v in os.environ.items() if not k.startswith("NIGHTCRAWLER_")}
        with mock.patch.dict(os.environ, env, clear=True):
            r = new_run.new_run("x", cwd=self.d, today=DAY)
        self.assertEqual(os.path.dirname(r["run_dir"]), os.path.join(self.d, "runs"))
        self.assertEqual(r["profile"], os.path.join(self.d, "profile.toml"))

    def test_cli_prints_json_and_rejects_empty_task(self):
        env = dict(os.environ, NIGHTCRAWLER_RUNS=self.d)
        out = subprocess.run([sys.executable, CLI, "agents", "returns"], capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(json.loads(out.stdout)["slug"].startswith("agents-returns-"))
        bad = subprocess.run([sys.executable, CLI], capture_output=True, text=True, env=env)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
