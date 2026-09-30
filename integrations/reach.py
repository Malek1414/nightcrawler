"""Research tools: Tavily, Jina Reader, Exa search, YouTube transcripts.

Principle: no function depends on a single service. Tavily needs a key and
costs credits; everything else keeps running for free. Without a key the
module behaves the same, just over the free routes.

- web_search(): web search. Tavily first (reliable, with a summary), falls
  back to Exa on error or without a key.
- read_page(): reads a page as clean text. First r.jina.ai (free, returns
  Markdown), then Tavily Extract (key only), finally a direct fetch with
  rough HTML stripping. With raw=True it fetches directly and returns the
  structured data embedded in the HTML (JSON-LD, __NEXT_DATA__ and friends)
  that the rendered text throws away.
- exa_search(): semantic web search over the free Exa MCP endpoint
  (JSON-RPC over HTTP; the reply is JSON or an SSE stream).
- youtube_transcript(): video subtitles via yt-dlp (local, free); without
  yt-dlp installed it returns a clear message instead of a traceback.

All blocking; runs inside the agent's tool loop.
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

JINA_READER = "https://r.jina.ai/"
EXA_MCP_URL = "https://mcp.exa.ai/mcp"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
_TIMEOUT = 40.0
_UA = "Mozilla/5.0 (compatible; Nightcrawler/1.0)"
MAX_PAGE_CHARS = 20000
MAX_SEARCH_CHARS = 8000



class PageCache:
    """Page cache for ONE run. The same URL is often read twice in a run (once
    to skim, once to cross-check); the second read should be free. Scoped per
    run on purpose: a process-wide cache would grow forever in a long-lived
    bot and serve last week's prices as current."""

    def __init__(self):
        self._pages: dict[tuple[str, bool], str] = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self._pages.get(key)

    def put(self, key, value: str) -> None:
        with self._lock:
            self._pages[key] = value


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) > max_chars:
        return (text[:max_chars]
                + f"\n[... truncated: showing {max_chars} of {len(text)} characters. "
                  "Facts near the end of the page are missing.]")
    return text


_BLOCK_RE = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
                       re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_JSON_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/(?:ld\+)?json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE)
_STATE_RE = re.compile(
    r"(window\.__[A-Z_]+__\s*=|window\.__remixContext\s*=)\s*(.{0,20000}?)</script>",
    re.DOTALL)


def _strip_html(raw: str) -> str:
    """Rough HTML-to-text reduction for the last-resort fallback."""
    text = _BLOCK_RE.sub(" ", raw)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _extract_data_blobs(raw: str) -> list[str]:
    """JSON-LD, __NEXT_DATA__, __NUXT__ and similar blobs from raw HTML."""
    blobs = [m.strip() for m in _JSON_SCRIPT_RE.findall(raw) if m.strip()]
    blobs += [f"{m[0]} {m[1].strip()}" for m in _STATE_RE.findall(raw)]
    return blobs


def _fetch_direct(url: str) -> str:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": _UA}) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return resp.text


def read_page(url: str, max_chars: int = MAX_PAGE_CHARS, tavily_key: str = "",
              raw: bool = False, cache: PageCache | None = None) -> str:
    """Fetch a page as text. Three stages, each only when the previous fails:

    1. Jina Reader (free, clean Markdown)
    2. Tavily Extract (needs a key, costs credits, gets into more pages)
    3. Direct fetch with rough HTML stripping (last resort)

    Tavily sits in the middle on purpose: Jina is free and good enough, so
    credits are only spent when Jina cannot handle a page.

    raw=True skips 1 and 2 and returns the embedded data blobs first, then the
    stripped text. That is the route for scraping structured data.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        # Search snippets often show bare domains ("example.org/events").
        url = "https://" + url
    key = (url, raw)
    if cache is not None and (hit := cache.get(key)) is not None:
        return hit

    result = _read_page_uncached(url, max_chars, tavily_key, raw)
    if cache is not None:
        cache.put(key, result)
    return result


def _read_page_uncached(url: str, max_chars: int, tavily_key: str, raw: bool) -> str:
    if raw:
        page = _fetch_direct(url)
        blobs = _extract_data_blobs(page)
        parts = []
        if blobs:
            parts.append("## Embedded data\n\n" + "\n\n".join(blobs))
        parts.append("## Page text\n\n" + _strip_html(page))
        return _truncate("\n\n".join(parts), max_chars)

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(JINA_READER + url)
            resp.raise_for_status()
        if resp.text.strip():
            return _truncate(resp.text, max_chars)
    except Exception as e:
        logger.warning("Jina Reader failed on %s (%s)", url, e)

    if tavily_key:
        try:
            return _truncate(tavily_extract(url, tavily_key), max_chars)
        except Exception as e:
            logger.warning("Tavily Extract failed on %s (%s)", url, e)

    return _truncate(_strip_html(_fetch_direct(url)), max_chars) or "The page is empty."


def tavily_extract(url: str, api_key: str) -> str:
    """Page content via Tavily. Raises on errors; the caller catches."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(TAVILY_EXTRACT_URL,
                           headers={"Authorization": f"Bearer {api_key}"},
                           json={"urls": [url]})
        resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise RuntimeError("Tavily extracted nothing")
    return (results[0].get("raw_content") or "").strip()


def _parse_mcp_response(resp: httpx.Response) -> dict:
    """Read an MCP reply, either plain JSON or an SSE event depending on the server."""
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise ValueError("SSE reply without a data line")
    return json.loads(resp.text)


def exa_search(query: str, num_results: int = 5) -> str:
    """Web search via Exa (free, no key). Returns hits as text."""
    headers = {"Accept": "application/json, text/event-stream",
               "Content-Type": "application/json"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(EXA_MCP_URL, headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "nightcrawler", "version": "1.0"}}})
        resp.raise_for_status()
        session_id = resp.headers.get("mcp-session-id")
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        client.post(EXA_MCP_URL, headers=headers,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        resp = client.post(EXA_MCP_URL, headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "web_search_exa",
                       "arguments": {"query": query,
                                     "numResults": max(1, min(int(num_results), 10))}}})
        resp.raise_for_status()
    data = _parse_mcp_response(resp)
    if "error" in data:
        raise RuntimeError(f"Exa search failed: {data['error']}")
    content = data.get("result", {}).get("content") or []
    texts = [part.get("text", "") for part in content if part.get("type") == "text"]
    result = "\n".join(t for t in texts if t).strip()
    return _truncate(result, MAX_SEARCH_CHARS) or "No results."


def _domain_list(domains: str) -> list[str]:
    """"example.com, foo.org" to a list. Empty stays empty."""
    return [d.strip().lstrip("*.") for d in (domains or "").split(",") if d.strip()]


def tavily_search(query: str, api_key: str, num_results: int = 5,
                  domains: str = "") -> str:
    """Web search via Tavily. Raises on errors; the caller catches."""
    payload = {"query": query,
               "max_results": max(1, min(int(num_results), 10)),
               "include_answer": True,
               "search_depth": "basic"}
    if _domain_list(domains):
        # Tavily filters server-side, which is more reliable than a site:
        # operator in the query text.
        payload["include_domains"] = _domain_list(domains)
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(TAVILY_SEARCH_URL,
                           headers={"Authorization": f"Bearer {api_key}"},
                           json=payload)
        resp.raise_for_status()
    data = resp.json()

    parts = []
    if data.get("answer"):
        parts.append(f"Summary: {data['answer']}\n")
    for hit in data.get("results") or []:
        title = (hit.get("title") or "untitled").strip()
        excerpt = re.sub(r"\s+", " ", (hit.get("content") or "")).strip()[:400]
        parts.append(f"- {title}\n  {hit.get('url', '')}\n  {excerpt}")
    if not parts:
        raise RuntimeError("Tavily returned no results")
    return _truncate("\n".join(parts), MAX_SEARCH_CHARS)


def web_search(query: str, num_results: int = 5, tavily_key: str = "",
               domains: str = "") -> str:
    """Web search with Tavily, falling back to Exa.

    Tavily first, because the free Exa MCP endpoint runs without a key and is
    correspondingly less reliable. Without a Tavily key only Exa remains.

    `domains` restricts to specific sites ("gov.uk, europa.eu"). Tavily can do
    that server-side. Exa cannot, so there it becomes a site: operator in the
    query: weaker, but better than dropping the filter silently.
    """
    if tavily_key:
        try:
            return tavily_search(query, tavily_key, num_results, domains)
        except Exception as e:
            logger.warning("Tavily search failed (%s), continuing with Exa", e)
    sites = _domain_list(domains)
    if sites:
        query = f"{query} " + " OR ".join(f"site:{d}" for d in sites)
    try:
        return exa_search(query, num_results)
    except httpx.HTTPError as e:
        # The free endpoint fails intermittently; one retry recovers most of it.
        logger.warning("Exa search failed (%s), retrying once", e)
        time.sleep(1.5)
        return exa_search(query, num_results)


# ---------------------------------------------------------- YouTube transcripts

def _parse_vtt(vtt: str) -> str:
    """VTT subtitles to plain text: drop timestamps, dedupe the rolling lines
    of auto-generated subs."""
    seen: set[str] = set()
    out: list[str] = []
    for raw_line in vtt.splitlines():
        line = raw_line.strip()
        if (not line or "-->" in line or line.isdigit()
                or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE"))):
            continue
        line = _TAG_RE.sub("", line).strip()
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return " ".join(out)


def youtube_transcript(url: str, max_chars: int = MAX_PAGE_CHARS,
                       sub_langs: str = "en,de,fr,es,ar") -> str:
    """Subtitles (including auto-subs) of a YouTube video as text."""
    exe = shutil.which("yt-dlp")
    if not exe:
        return ("yt-dlp is not installed on this system, so no transcript "
                "(pip install yt-dlp).")
    primary = sub_langs.split(",")[0].strip()
    with tempfile.TemporaryDirectory(prefix="nightcrawler-yt-") as tmp:
        cmd = [exe, "--skip-download", "--write-subs", "--write-auto-subs",
               "--sub-langs", sub_langs, "--sub-format", "vtt",
               "-o", str(Path(tmp) / "sub"), "--", url]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return "Timed out while loading the subtitles."
        vtts = sorted(Path(tmp).glob("*.vtt"))
        if not vtts:
            return "This video has no subtitles."
        preferred = [p for p in vtts if f".{primary}" in p.name]
        pick = (preferred or vtts)[0]
        text = _parse_vtt(pick.read_text(encoding="utf-8", errors="replace"))
        return _truncate(text, max_chars) or "The subtitles were empty."
