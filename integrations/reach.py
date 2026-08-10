"""Recherche-Werkzeuge: Tavily, Jina Reader, Exa-Suche, YouTube-Transkripte.

Grundsatz: keine Funktion hängt an einem einzelnen Dienst. Tavily braucht einen
Key und kostet Credits, alles andere läuft kostenlos weiter. Ohne Key verhält
sich das Modul genauso, nur über die freien Wege.

- web_search(): Websuche. Tavily zuerst (zuverlässig, mit Zusammenfassung),
  bei Fehler oder ohne Key zurück auf Exa.
- read_page(): liest eine Webseite als sauberen Text. Erst r.jina.ai (gratis,
  liefert Markdown), dann Tavily Extract (nur mit Key), zuletzt direkter Abruf
  plus grobe HTML-Entfernung.
- exa_search(): semantische Websuche über den kostenlosen Exa-MCP-Endpoint
  (JSON-RPC über HTTP, Antwort kommt als JSON oder SSE-Stream).
- youtube_transcript(): Untertitel eines Videos über yt-dlp (lokal, kostenlos);
  ohne installiertes yt-dlp gibt es eine klare Meldung statt eines Tracebacks.

Alles blockierend, läuft im Tool-Loop des Agents.
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

JINA_READER = "https://r.jina.ai/"
EXA_MCP_URL = "https://mcp.exa.ai/mcp"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
_TIMEOUT = 40.0
_UA = "Mozilla/5.0 (compatible; ResearchAgent/1.0)"
MAX_PAGE_CHARS = 7000


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n[... gekürzt]"
    return text


_BLOCK_RE = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
                       re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    """Grobe HTML-zu-Text-Reduktion für den Jina-Fallback."""
    text = _BLOCK_RE.sub(" ", raw)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def read_page(url: str, max_chars: int = MAX_PAGE_CHARS, tavily_key: str = "") -> str:
    """Webseite als Text holen. Drei Stufen, jede greift erst, wenn die vorige scheitert:

    1. Jina Reader (kostenlos, liefert sauberes Markdown)
    2. Tavily Extract (braucht Key, kostet Credits, kommt an mehr Seiten ran)
    3. Seite direkt holen und HTML grob strippen (letzte Rettung)

    Tavily sitzt bewusst in der Mitte: Jina ist gratis und gut genug, Credits
    werden also nur verbraucht, wenn Jina eine Seite nicht packt.

    Für Scraping wichtig: Stufe 3 liefert rohes HTML ohne Tags, darin sind
    JSON-Marker wie __NEXT_DATA__ noch sichtbar. Stufe 1 rendert die Seite
    lesbar, wirft solche Blobs aber weg. Siehe skills/web-scraping.md.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(JINA_READER + url)
            resp.raise_for_status()
        if resp.text.strip():
            return _truncate(resp.text, max_chars)
    except Exception as e:
        logger.warning("Jina Reader scheiterte an %s (%s)", url, e)

    if tavily_key:
        try:
            return _truncate(tavily_extract(url, tavily_key), max_chars)
        except Exception as e:
            logger.warning("Tavily Extract scheiterte an %s (%s)", url, e)

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": _UA}) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return _truncate(_strip_html(resp.text), max_chars) or "Die Seite ist leer."


def tavily_extract(url: str, api_key: str) -> str:
    """Seiteninhalt über Tavily holen. Wirft bei Fehlern, der Aufrufer fängt."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(TAVILY_EXTRACT_URL,
                           headers={"Authorization": f"Bearer {api_key}"},
                           json={"urls": [url]})
        resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise RuntimeError("Tavily hat nichts extrahiert")
    return (results[0].get("raw_content") or "").strip()


def _parse_mcp_response(resp: httpx.Response) -> dict:
    """MCP-Antwort lesen, je nach Server JSON direkt oder als SSE-Event."""
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise ValueError("SSE-Antwort ohne data-Zeile")
    return json.loads(resp.text)


def exa_search(query: str, num_results: int = 5) -> str:
    """Websuche über Exa (kostenlos, ohne Key). Liefert Treffer als Text."""
    headers = {"Accept": "application/json, text/event-stream",
               "Content-Type": "application/json"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(EXA_MCP_URL, headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "research-agent", "version": "1.0"}}})
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
        raise RuntimeError(f"Exa-Suche fehlgeschlagen: {data['error']}")
    content = data.get("result", {}).get("content") or []
    texts = [part.get("text", "") for part in content if part.get("type") == "text"]
    result = "\n".join(t for t in texts if t).strip()
    return _truncate(result, MAX_PAGE_CHARS) or "Keine Treffer."


def _domain_list(domains: str) -> list[str]:
    """"example.com, foo.org" zu einer Liste. Leer bleibt leer."""
    return [d.strip().lstrip("*.") for d in (domains or "").split(",") if d.strip()]


def tavily_search(query: str, api_key: str, num_results: int = 5,
                  domains: str = "") -> str:
    """Websuche über Tavily. Wirft bei Fehlern, der Aufrufer fängt."""
    payload = {"query": query,
               "max_results": max(1, min(int(num_results), 10)),
               "include_answer": True,
               "search_depth": "basic"}
    if _domain_list(domains):
        # Tavily filtert serverseitig, das ist zuverlässiger als ein
        # site:-Operator im Suchtext.
        payload["include_domains"] = _domain_list(domains)
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(TAVILY_SEARCH_URL,
                           headers={"Authorization": f"Bearer {api_key}"},
                           json=payload)
        resp.raise_for_status()
    data = resp.json()

    teile = []
    if data.get("answer"):
        teile.append(f"Zusammenfassung: {data['answer']}\n")
    for hit in data.get("results") or []:
        titel = (hit.get("title") or "ohne Titel").strip()
        auszug = re.sub(r"\s+", " ", (hit.get("content") or "")).strip()[:400]
        teile.append(f"- {titel}\n  {hit.get('url', '')}\n  {auszug}")
    if not teile:
        raise RuntimeError("Tavily lieferte keine Treffer")
    return _truncate("\n".join(teile), MAX_PAGE_CHARS)


def web_search(query: str, num_results: int = 5, tavily_key: str = "",
               domains: str = "") -> str:
    """Websuche mit Tavily, fällt auf Exa zurück.

    Tavily zuerst, weil der freie Exa-MCP-Endpoint ohne Key läuft und
    entsprechend unzuverlässig ist. Ohne Tavily-Key bleibt nur Exa.

    `domains` schränkt auf bestimmte Seiten ein ("bund.de, destatis.de").
    Tavily kann das serverseitig. Exa nicht, dort wandert es als
    site:-Operator in die Anfrage: schwächer, aber besser als nichts.
    """
    if tavily_key:
        try:
            return tavily_search(query, tavily_key, num_results, domains)
        except Exception as e:
            logger.warning("Tavily-Suche scheiterte (%s), weiter mit Exa", e)
    liste = _domain_list(domains)
    if liste:
        query = f"{query} " + " OR ".join(f"site:{d}" for d in liste)
    return exa_search(query, num_results)


# ------------------------------------------------------- YouTube-Transkripte

def _parse_vtt(vtt: str) -> str:
    """VTT-Untertitel zu Fließtext: Zeitmarken raus, Wiederholungen der
    Auto-Subs (rollende Zeilen) deduplizieren."""
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
                       sub_langs: str = "de,en") -> str:
    """Untertitel (auch Auto-Subs) eines YouTube-Videos als Text."""
    exe = shutil.which("yt-dlp")
    if not exe:
        return ("yt-dlp ist auf diesem System nicht installiert, "
                "Transkript nicht möglich (pip install yt-dlp).")
    primary = sub_langs.split(",")[0].strip()
    with tempfile.TemporaryDirectory(prefix="research-yt-") as tmp:
        cmd = [exe, "--skip-download", "--write-subs", "--write-auto-subs",
               "--sub-langs", sub_langs, "--sub-format", "vtt",
               "-o", str(Path(tmp) / "sub"), "--", url]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return "Zeitüberschreitung beim Laden der Untertitel."
        vtts = sorted(Path(tmp).glob("*.vtt"))
        if not vtts:
            return "Für dieses Video gibt es keine Untertitel."
        preferred = [p for p in vtts if f".{primary}" in p.name]
        pick = (preferred or vtts)[0]
        text = _parse_vtt(pick.read_text(encoding="utf-8", errors="replace"))
        return _truncate(text, max_chars) or "Untertitel waren leer."
