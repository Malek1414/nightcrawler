"""Unit tests for search.py: URL canonicalisation, merge ranking, fallback chain, shared seen-list."""
import os
import sys
import tempfile
import threading
import types
import unittest
from datetime import date, timedelta
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "research-agent", "references"))
import search  # noqa: E402


def opts(**kw):
    base = dict(engine=None, fan=False, site=[], exclude=[], n=10)
    base.update(kw)
    return types.SimpleNamespace(**base)


class NormUrl(unittest.TestCase):
    def test_strips_tracking_www_scheme_and_slash(self):
        a = search.norm_url("http://www.Example.com/path/?utm_source=x&id=7&fbclid=abc")
        b = search.norm_url("https://example.com/path?id=7")
        self.assertEqual(a, b)

    def test_keeps_meaningful_query(self):
        self.assertNotEqual(search.norm_url("https://a.de/?p=1"), search.norm_url("https://a.de/?p=2"))


class Merge(unittest.TestCase):
    def test_hits_found_by_several_engines_rank_first(self):
        hits = [
            search.hit("solo", "https://solo.org/x", "", "", "tavily"),
            search.hit("both", "https://www.both.org/y/", "", "", "tavily"),
            search.hit("both", "https://both.org/y?utm_medium=z", "snippet", "2026-09-01", "serper"),
        ]
        out = search.merge(hits)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["title"], "both")
        self.assertEqual(out[0]["engine"], "tavily+serper")
        self.assertEqual(out[0]["snippet"], "snippet")
        self.assertEqual(out[0]["published"], "2026-09-01")

    def test_same_engine_twice_is_not_double_counted(self):
        hits = [search.hit("a", "https://a.org", "", "", "exa")] * 2
        self.assertEqual(search.merge(hits)[0]["engine"], "exa")


class HostFilter(unittest.TestCase):
    def test_site_matches_subdomains_only(self):
        o = opts(site=["berlin.de"])
        self.assertTrue(search.host_ok({"url": "https://www.bildung.berlin.de/a"}, o))
        self.assertFalse(search.host_ok({"url": "https://notberlin.de/a"}, o))

    def test_exclude(self):
        o = opts(exclude=["pinterest.com"])
        self.assertFalse(search.host_ok({"url": "https://de.pinterest.com/pin/1"}, o))


class SinceDate(unittest.TestCase):
    def test_relative_and_absolute(self):
        self.assertEqual(search.since_date("7d"), date.today() - timedelta(days=7))
        self.assertEqual(search.since_date("2026-09-01"), date(2026, 9, 1))
        self.assertIsNone(search.since_date(None))


class FallbackChain(unittest.TestCase):
    def test_falls_through_down_and_empty_engines(self):
        def down(q, o, k):
            raise search.EngineDown("HTTP 429")
        fake = {name: down for name in search.CHAIN}
        fake[search.CHAIN[1]] = lambda q, o, k: []
        fake[search.CHAIN[2]] = lambda q, o, k: [search.hit("t", "https://ok.org", "", "", search.CHAIN[2])]
        log = []
        with mock.patch.dict(search.ENGINES, fake):
            hits = search.run_query("q", opts(), {}, log)
        self.assertEqual([h["engine"] for h in hits], [search.CHAIN[2]])
        self.assertEqual(log, [f"{search.CHAIN[0]}: HTTP 429", f"{search.CHAIN[1]}: 0 Treffer"])

    def test_fan_queries_all_engines_and_survives_failures(self):
        def down(q, o, k):
            raise search.EngineDown("kein Key")
        fake = {name: (lambda n: lambda q, o, k: [search.hit(n, f"https://{n}.org", "", "", n)])(name)
                for name in search.CHAIN}
        fake[search.CHAIN[0]] = down
        log = []
        with mock.patch.dict(search.ENGINES, fake):
            hits = search.run_query("q", opts(fan=True), {}, log)
        self.assertEqual(len(hits), len(search.CHAIN) - 1)
        self.assertEqual(len(log), 1)


class Keys(unittest.TestCase):
    def test_env_file_ignores_inline_comments_and_empty_values(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w") as f:
                f.write("EXA_API_KEY=          # exa.ai free tier\n"
                        "export SERPER_API_KEY='abc123'  # comment\n"
                        "OTHER=ignored\n")
            with mock.patch.object(search, "KEY_FILES", [env]), mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(search.load_keys(), {"SERPER_API_KEY": "abc123"})

    def test_environment_wins_over_file(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w") as f:
                f.write("TAVILY_API_KEY=from-file\n")
            with mock.patch.object(search, "KEY_FILES", [env]), \
                    mock.patch.dict(os.environ, {"TAVILY_API_KEY": "from-env"}, clear=True):
                self.assertEqual(search.load_keys()["TAVILY_API_KEY"], "from-env")


class SeenList(unittest.TestCase):
    def test_parallel_agents_never_record_a_url_twice(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "wave", "seen.txt")
            urls = [f"https://site{i % 25}.org/page" for i in range(200)]

            def agent(chunk):
                hits = search.merge([search.hit("t", u, "", "", "exa") for u in chunk])
                search.mark_seen(hits, path)

            threads = [threading.Thread(target=agent, args=(urls[i::8],)) for i in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            with open(path) as f:
                keys = [line.split("\t")[0] for line in f]
            self.assertEqual(len(keys), 25)
            self.assertEqual(len(set(keys)), 25)

    def test_marks_new_and_known(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "seen.txt")
            first = search.merge([search.hit("a", "https://a.org", "", "", "exa")])
            search.mark_seen(first, path)
            again = search.merge([search.hit("a", "https://www.a.org/", "", "", "serper"),
                                  search.hit("b", "https://b.org", "", "", "serper")])
            search.mark_seen(again, path)
            self.assertEqual({h["title"]: h["new"] for h in again}, {"a": False, "b": True})


if __name__ == "__main__":
    unittest.main()
