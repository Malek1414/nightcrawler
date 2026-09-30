"""Research tools: only the pure text functions, no network."""

from __future__ import annotations

from integrations import reach


def test_strip_html_drops_script_and_style():
    raw = """
    <html><head><style>body{color:red}</style></head>
    <body><script>var x = 1;</script><h1>Title</h1><p>Text &amp; more</p></body></html>
    """
    text = reach._strip_html(raw)
    assert "Title" in text and "Text & more" in text
    assert "var x" not in text and "color:red" not in text


def test_strip_html_drops_json_ld():
    """Stripping also removes script blobs. That is why raw mode extracts
    them separately first."""
    raw = '<script type="application/ld+json">{"name":"Event"}</script><p>Hello</p>'
    assert "Event" not in reach._strip_html(raw)


def test_extract_data_blobs_finds_json_ld_and_state():
    raw = ('<script type="application/ld+json">{"@type":"Event","name":"Demo Day"}</script>'
           '<script id="__NEXT_DATA__" type="application/json">{"props":{"x":1}}</script>'
           '<script>window.__NUXT__={"y":2}</script><p>Hi</p>')
    blobs = reach._extract_data_blobs(raw)
    joined = "\n".join(blobs)
    assert '"Demo Day"' in joined and '"props"' in joined and '{"y":2}' in joined


def test_raw_mode_puts_embedded_data_first(monkeypatch):
    monkeypatch.setattr(reach, "_fetch_direct", lambda url: (
        '<script type="application/ld+json">{"price":"0"}</script><p>Body</p>'))
    out = reach.read_page("https://ex.com/e", raw=True)
    assert out.index("Embedded data") < out.index("Page text")
    assert '"price":"0"' in out


def test_read_page_is_cached_per_run(monkeypatch):
    calls = []
    monkeypatch.setattr(reach, "_fetch_direct", lambda url: calls.append(url) or "<p>x</p>")
    run1, run2 = reach.PageCache(), reach.PageCache()
    reach.read_page("https://ex.com/c", raw=True, cache=run1)
    reach.read_page("https://ex.com/c", raw=True, cache=run1)
    assert calls == ["https://ex.com/c"]
    # A new run must fetch fresh, so prices are never served from last week.
    reach.read_page("https://ex.com/c", raw=True, cache=run2)
    assert len(calls) == 2


def test_read_page_without_cache_always_fetches(monkeypatch):
    calls = []
    monkeypatch.setattr(reach, "_fetch_direct", lambda url: calls.append(url) or "<p>x</p>")
    reach.read_page("https://ex.com/c", raw=True)
    reach.read_page("https://ex.com/c", raw=True)
    assert len(calls) == 2


def test_read_page_accepts_bare_domains(monkeypatch):
    """Search snippets often show "example.org/events" without a scheme."""
    seen = []
    monkeypatch.setattr(reach, "_fetch_direct", lambda url: seen.append(url) or "<p>x</p>")
    reach.read_page("example.org/events", raw=True)
    assert seen == ["https://example.org/events"]


def test_exa_is_retried_once(monkeypatch):
    import httpx

    monkeypatch.setattr(reach.time, "sleep", lambda s: None)
    attempts = []

    def flaky(query, n=5):
        attempts.append(query)
        if len(attempts) == 1:
            raise httpx.HTTPError("502")
        return "hits"
    monkeypatch.setattr(reach, "exa_search", flaky)
    assert reach.web_search("q") == "hits" and len(attempts) == 2


def test_truncate_says_how_much_is_missing():
    assert reach._truncate("abcdef", 100) == "abcdef"
    cut = reach._truncate("abcdef", 3)
    assert cut.startswith("abc") and "3 of 6" in cut


def test_parse_vtt_removes_timestamps_and_duplicates():
    vtt = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
Hello everyone

00:00:03.000 --> 00:00:05.000
Hello everyone
today is about <c>scraping</c>
"""
    text = reach._parse_vtt(vtt)
    assert text == "Hello everyone today is about scraping"
    assert "-->" not in text and "WEBVTT" not in text


def test_domain_list_cleans_the_input():
    assert reach._domain_list("europa.eu, oecd.org") == ["europa.eu", "oecd.org"]
    assert reach._domain_list("*.europa.eu") == ["europa.eu"]
    assert reach._domain_list("") == []
    assert reach._domain_list(" , ") == []


def test_without_tavily_key_domain_filter_moves_into_query(monkeypatch):
    """Exa cannot filter server-side. Instead of dropping the filter silently,
    it is appended as a site: operator."""
    seen = {}
    monkeypatch.setattr(reach, "exa_search",
                        lambda query, n=5: seen.setdefault("q", query) or "ok")

    reach.web_search("rent index", domains="europa.eu, oecd.org")
    assert "site:europa.eu OR site:oecd.org" in seen["q"]


def test_without_domains_query_is_unchanged(monkeypatch):
    seen = {}
    monkeypatch.setattr(reach, "exa_search",
                        lambda query, n=5: seen.setdefault("q", query) or "ok")

    reach.web_search("rent index")
    assert seen["q"] == "rent index"


def test_youtube_transcript_without_ytdlp_says_so(monkeypatch):
    monkeypatch.setattr(reach.shutil, "which", lambda _: None)
    answer = reach.youtube_transcript("https://youtu.be/xyz")
    assert "yt-dlp" in answer and "not installed" in answer
