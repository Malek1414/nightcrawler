# Kanäle, Werkzeuge, Fallback-Ketten

Verderbliche Details (Preise, Rate-Limits, Endpunkte) stehen NUR hier, nicht im
SKILL.md. Zahlen und Endpunkte gegen die Anbieterseite prüfen, bevor du dich
darauf verlässt; Gelerntes als eine Zeile nachtragen.

## Schon da (nichts installieren)
- **agent-reach** ist der Router für 15 Plattformen. Bei Login-Plattformen
  (Reddit, X, Instagram, Xiaohongshu) zuerst `agent-reach doctor --json`, dann
  den active_backend nehmen. Websuche `mcporter call exa.web_search_exa`,
  Seiten `curl https://r.jina.ai/<URL>`, YouTube `yt-dlp`.
- **WebSearch** (Harness): Topf ca. 200 pro Session, geteilt mit allen
  Subagents. Nach 3 bis 4 Agents leer, darum sparsam und erst nach den keyless
  Kanälen.
- **Tavily** (`TAVILY_API_KEY`), Free 1000 Credits pro Monat.
- **LinkedIn ohne Login** (belegt 15.09.2026): Tavily mit
  `"include_domains":["linkedin.com"]` liefert Profil-Snippets mit Titel und
  Ort, reicht für Lead-Listen ohne WebSearch. Der
  agent-reach-LinkedIn-Scraper ist aus, s.jina.ai verlangt inzwischen einen Key.
- **Browser-MCP** (lokaler Browser) für Google und DuckDuckGo, wenn curl
  blockt: `navigate_page` plus `take_snapshot`. Hat bei Kalender-Aggregatoren
  zuverlässig funktioniert.

## Zuerst einrichten (löst die dokumentierten Limits)
- **Jina Free-Key**: hebt r.jina.ai von 20 auf 500 Anfragen pro Minute, dazu
  s.jina.ai als Suche. Key aus der Umgebung (`JINA_API_KEY`), Header
  `Authorization: Bearer $JINA_API_KEY`. Löst den 429 ab dem zweiten parallelen
  Batch. Registrierung: jina.ai.
- **Hound** (Repo dondai1234/master-fetch, MIT, VOR Installation vetten, siehe
  unten): ein MCP mit keyless Suche über mehrere Engines parallel plus lokalem
  Rerank, `smart_fetch` mit HTTP-zuerst und Auto-Eskalation in einen
  Stealth-Browser, `focus="..."` liefert nur die relevanten Blöcke (spart viel
  Kontext), BYOK-Key-Stapel mit Auto-Rotation bei 429. Ersetzt Exa-Free,
  Jina-Limit und curl-Blocker in einem. Install `pip install hound-mcp[all]`.
- **Key-Stapel (Free-Tiers, keine Karte)**: Exa (Startguthaben plus monatliches
  Freikontingent), Serper (einmaliges Google-SERP-Kontingent), Parallel
  (monatliches Freikontingent). Keys aus der Umgebung, siehe .env.example.
  Zusammen mit Tavily weit über die WebSearch-Grenze hinaus, ohne Kosten.
- **agent-browser** (Repo vercel-labs/agent-browser) als Server-Browser für den
  Server, deutlich tokensparsamer als Playwright-MCP. Lokal bleibt der Browser-MCP.

## Fetch-Leiter (fail-closed)
1. Keyless bzw. günstig: Hound `smart_search` / Fachquelle-API (unten).
2. Seite lesen: Hound `smart_fetch` oder `curl https://r.jina.ai/<URL>` (mit
   Key sequenziell ab dem zweiten Batch), sonst WebFetch.
3. Blockt curl: Browser-MCP (lokal) oder agent-browser (Server).
4. HTTP 200 prüfen: echte Inhalts-Seite oder Cloudflare/Consent? Letzteres zählt
   nicht.

## Fachquellen als Werkzeug (dienen der echten Arbeit)
- **EU Funding and Tenders Search API** (keyless, INOFFIZIELL, Endpunkt gegen
  ec.europa.eu prüfen): Programm-IDs wie Erasmus+, Horizon, Creative Europe.
- **JedeSchule API** (jedeschule.codefor.de/docs): Schulen in Deutschland mit
  stabilen IDs als API und CSV.
- **OffeneRegister.de**: Handelsregister-Firmen und Officers, SQLite oder JSONL.
- **HN Algolia** (hn.algolia.com/api) und **Arctic Shift**
  (arctic-shift.photon-reddit.com/api): Hacker News und Reddit lesen, keyless.
- **arXiv / Semantic Scholar / OpenAlex**: Paper und Zitationsgraph, MCP-Server
  vorhanden.
- Aus früheren Läufen mit offener API: mymun (locations/continent,
  conferences/by-slug), youth.europa.eu/solidarity (search_en). Per curl nutzbar.

## Plattform-Lage 2026 (aus Recherche 08.09.2026, prüfen)
- **X/Twitter**: API Pay-per-use, kein Free-Tier. Lesen keyless nur über Hound
  bzw. Nitter/xcancel (fragil), Cookie-Backend über agent-reach.
- **Reddit**: Developer-Apps nur per Antrag. Lesen keyless über Arctic Shift
  oder Hound (old.reddit), RSS über reddit-mcp-buddy.
- **Reddit-Lage 27.09.2026 (belegt)**: reddit.com/.json und old.reddit per curl
  403, r.jina.ai liefert leer, WebSearch mit `allowed_domains: reddit.com`
  wird abgelehnt. Funktioniert: Exa (`exa.web_search_exa`, optional
  `startPublishedDate`), liefert Posts samt Kommentar-Auszügen, Suchbegriff mit
  "reddit" plus Subreddit-Name beginnen. Erster Griff für Reddit-Fragen.
- **mcporter aus dem Home-Ordner aufrufen**: in einem anderen Arbeitsverzeichnis meldet
  es "Unknown MCP server 'exa'" (Config wird relativ gefunden).
- **Affiliate-Fanseiten** (z.B. kakoguide.com für Kakobuy) sind keine
  neutralen Vergleiche, Aussagen gegen Nutzerberichte gegenprüfen.
- **Brave Search API**: Free-Tier gestrichen, Karte nötig, darum nicht im Stapel.

## Blockt curl/WebFetch komplett (nur Browser)
coe.int, obessu.org, mymun.com (hat aber offene API, siehe oben), SALTO-Kalender
(nur Browse-Filter im Browser), members.eyp.org (Login). Direkt zum Browser
statt Zeit mit curl verlieren.

## Vor Installation fremder Tools/Skills vetten
Hound, agent-browser und jeder fremde Skill sind Fremdcode. Vor `pip install`
oder dem Kopieren nach ~/.claude: mit einem Security-Review bzw. SkillSpector auf
Prompt-Injection, verdächtige Netzwerkziele und Rug-Pull-Muster prüfen. Kein
blindes `install` aus einer Repo-Beschreibung.

## Belege prüfen
Zitate und URLs über `references/sources.py` führen und vor "fertig" mit
`sources.py verify` gegenprüfen.

## Umgebungsvariablen
Keys kommen aus der Umgebung oder einer lokalen .env, nie in dieses Skill. Welche,
steht in `.env.example`.
