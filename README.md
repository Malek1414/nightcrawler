# Recherche- und Scraping-Agent (Skelett)

Ein Agent, der eine Frage nimmt, das Web durchsucht, Seiten wirklich liest,
strukturierte Daten aus ihnen zieht und eine belegte Antwort zurückgibt. Er
hört nicht beim ersten Treffer auf, und er prüft jede Zahl gegen eine zweite
Quelle, bevor er sie behauptet.

Das hier ist das **Skelett**: die komplette Logik und alle Methoden, ohne Daten
von irgendwem. Du trägst deine eigenen Zugangsdaten in eine `.env` ein und es
läuft auf deinem Rechner.

> **Neu hier?** Die Schritt-für-Schritt-Einrichtung steht in
> **[SETUP.md](SETUP.md)**, geschrieben als Rezept, das du auch direkt einem
> Coding-Agenten (Claude Code, Cursor, Codex) geben kannst.

---

## Wie er arbeitet

Das Besondere steckt nicht im Code, sondern in der Arbeitsweise, die im
System-Prompt und in den Skills festgeschrieben ist:

**Suchfächer statt Einzelsuche.** Auf jede Frage gehen mindestens drei
Suchanfragen gleichzeitig raus: der Begriff wörtlich, ein Synonym oder
Fachbegriff, die englische Variante. Danach wird verglichen, welche
Formulierung frische und offizielle Quellen bringt. Nur diese Spur wird
verfeinert.

**Lesen statt Snippets sammeln.** Mindestens sechs Treffer aus mindestens vier
Domains werden im Volltext gelesen. Ein Suchsnippet ist kein Beleg.

**Gegencheck als Pflicht.** Jede Zahl, jedes Datum, jeder Preis und jeder Name
läuft gegen eine zweite, unabhängige Quelle. Was nur an einer Quelle hängt,
wird als `[unbestätigt]` markiert. Widersprechen sich zwei Quellen, stehen
beide Werte in der Antwort, statt dass sich der Agent einen aussucht.

**Abbruchkriterium.** Fertig ist er erst, wenn eine weitere Runde nur noch
Bekanntes bringt, nicht schon wenn eine plausible Antwort dasteht.

---

## Architektur

Ein Auftrag läuft immer denselben Weg:

```
main.py            CLI, oder dein eigener Aufrufer (Bot, Web-Backend, anderer Agent)
      |
  agent.py         System-Prompt (die Arbeitsweise) + Tool-Definitionen
      |
 core/llm.py       Tool-Loop: Modell fragen, Tools ausführen, wiederholen
      |            lesende Tools laufen gleichzeitig, schreibende nacheinander
      |
      +-- core/skills.py         lädt skills/*.md bei Bedarf nach
      +-- integrations/reach.py  Suche, Seiten lesen, YouTube-Transkripte
      +-- integrations/notes.py  Markdown-Ordner lesen und beschreiben
```

| Datei / Ordner | Was drin liegt |
|---|---|
| `main.py` | Einstieg von der Kommandozeile |
| `agent.py` | System-Prompt, Tool-Schemas, Handler. Der Ort, an dem sich Verhalten ändert |
| `core/llm.py` | Tool-Loop, paralleles Ausführen lesender Tools, Mock-Modus, Token-Zählung |
| `core/skills.py` | Skill-Loader: Frontmatter parsen, Index bauen, `read_skill` bereitstellen |
| `core/config.py` | `.env` einlesen. Keine Werte im Code |
| `integrations/reach.py` | Tavily, Exa, Jina Reader, yt-dlp. Jede Funktion mit Fallback |
| `integrations/notes.py` | Notiz-Ordner: suchen, lesen, neu anlegen (nie überschreiben) |
| `integrations/web_search.py` | Notausgang, falls der Tool-Loop komplett scheitert |
| `skills/*.md` | Die ausführlichen Methoden. Neue Methode = neue Datei, kein Code |
| `beispiele/` | Vorlage für die Zielgruppen-Notiz |
| `tests/` | Läuft ohne Netz und ohne API-Key |

---

## Werkzeuge

| Tool | Was es tut | Fällt zurück auf |
|---|---|---|
| `web_search` | Websuche mit Kurzzusammenfassung, optional auf bestimmte Domains eingegrenzt | Tavily (filtert Domains serverseitig), dann Exa (kostenlos, ohne Key, bekommt `site:` in die Anfrage) |
| `read_page` | Seite als sauberer Text | Jina Reader, dann Tavily Extract, dann roher Abruf mit HTML-Strippen |
| `youtube_transcript` | Untertitel eines Videos, auch Auto-Subs | yt-dlp lokal. Fehlt es, sagt der Agent das statt zu crashen |
| `search_notes` | Eigene Notizen durchsuchen | nur aktiv mit `NOTES_DIR` |
| `read_note` | Eine Notiz lesen | nur aktiv mit `NOTES_DIR` |
| `save_research` | Ergebnis als Markdown-Notiz ablegen | nur aktiv mit `NOTES_DIR` |
| `read_skill` | Eine Methode nachladen | immer da |

Keine Funktion hängt an einem einzelnen Dienst. Ohne Tavily-Key läuft alles
über die kostenlosen Wege, nur etwas wackliger.

---

## Skills

Skills sind der Grund, warum der Prompt klein bleibt. Im System-Prompt steht
nur der Index (Name plus ein Satz). Den vollen Text lädt der Agent über
`read_skill` selbst nach, wenn die Aufgabe dazu passt. Nach dem Prinzip der
Anthropic Agent Skills.

| Skill | Wofür |
|---|---|
| `web-scraping` | Daten statt Prosa: offene Datensätze (CKAN, Socrata), JSON im HTML (`__NEXT_DATA__` und Verwandte, JSON-LD), Endpunkte (`/wp-json/`, `/products.json`), Paginierung abtasten, Grenzen des Werkzeugs |
| `seiten-index` | Alle URLs einer Domain auf einmal: robots.txt, Sitemaps, News-Sitemaps, Wayback-Index |
| `archiv-recherche` | Tote, gesperrte oder geänderte Seiten über das Internet Archive holen und Stände vergleichen |
| `such-operatoren` | Verengen, wenn der Suchfächer nur Rauschen bringt: Domain-Filter, `filetype:`, exakte Phrase |
| `deep-research` | Frage zerlegen, Quellenregister führen, Gegenthese suchen, belegen |
| `quellenarbeit` | Vollständige Quellenangaben für Schule und Uni, Zitat gegen Paraphrase |
| `lead-recherche` | Leads suchen und gegen die eigene Zielgruppen-Notiz filtern |

**Warum vier Skills fürs Scraping und nicht einer oder acht:** Geschnitten ist
nach *Auslöser*, nicht nach Thema. `web-scraping` greift, wenn du Daten aus
einer bekannten Seite ziehst. `seiten-index`, wenn du die Seiten erst noch
finden musst. `archiv-recherche`, wenn die Seite nicht mehr da ist.
`such-operatoren`, wenn die Suche nichts Brauchbares liefert. Vier verschiedene
Situationen, kein Überschneiden, und der Agent lädt nur die eine, die passt.

Ein reiner Wegweiser-Skill, der nur auf andere verweist, wäre dagegen eine
verschenkte Tool-Runde: die Weiche steht kostenlos im System-Prompt, den das
Modell ohnehin sieht. Deshalb hält `web-scraping` seine Details selbst.

Drei Tests halten das zusammen: jeder Querverweis muss auf einen existierenden
Skill zeigen, kein Skill darf sich selbst empfehlen, und keiner darf über
`MAX_SKILL_CHARS` wachsen (sonst kappt `read_skill` still genau die Abschnitte
am Ende, in denen die Grenzen und der Anstand stehen).

**Neuen Skill hinzufügen**: eine `.md` in `skills/` ablegen, mit Frontmatter:

```markdown
---
name: mein-skill
description: Ein Satz, der im Index steht und entscheidet, ob der Agent lädt
agents: research
---
# Mein Skill

Die Anleitung.
```

Kein Code, kein Neustart-Ritual. Beim nächsten Lauf ist der Skill im Index.

---

## Schnellstart

```bash
cp .env.example .env          # dann .env ausfüllen (mindestens OPENAI_API_KEY)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python main.py "Was kostet ein Lastenrad-Abo in Berlin?"
```

Weitere Aufrufe:

```bash
.venv/bin/python main.py --skills            # welche Methoden gibt es
.venv/bin/python main.py --prompt            # den fertigen System-Prompt sehen
.venv/bin/python main.py --mock "Testfrage"  # ohne API-Aufruf durchlaufen
echo "Auftrag" | .venv/bin/python main.py    # aus einer Pipe
.venv/bin/python -m pytest                   # Tests, ohne Netz und ohne Key
```

**Einbauen statt aufrufen:** Der Agent hängt an keinem Kanal. Wer ihn in einen
Bot oder ein Web-Backend steckt, ruft `agent.run(config, auftrag)` auf und
bekommt den fertigen Text. Der Aufruf blockiert, gehört in einem async-Programm
also in `asyncio.to_thread()`.

---

## Kosten

Der einzige zwingend bezahlte Dienst ist die LLM-API. Ein Tavily-Key macht die
Suche zuverlässiger und kostet Credits, ist aber optional: ohne Key läuft die
Suche über den freien Exa-Endpoint. Jina Reader und yt-dlp sind kostenlos.

Eine gründliche Recherche zieht mehr Tokens als ein normaler Chat, weil sechs
und mehr Seiten im Volltext durchs Modell gehen. `MAX_ROUNDS` begrenzt das nach
oben. Nach jedem Lauf steht der Verbrauch auf stderr.

## Sicherheit

- Secrets stehen ausschließlich in der `.env`, nie im Code. Die `.env` ist in
  `.gitignore`. Landet doch mal ein Key im Repo, hilft nur: Key neu erzeugen.
- Notiz-Pfade werden gegen den Wurzelordner geprüft, damit ein erfundenes
  `../../.ssh/id_rsa` nicht durchkommt.
- `create_note` legt nur neue Dateien an und überschreibt nie eine bestehende.
- Fehler in Tools gehen als Text zurück ans Modell statt als Absturz, damit der
  Agent auf einen kaputten Abruf reagieren kann.
- Der Scraping-Skill sagt ausdrücklich: robots.txt respektieren, keine
  Bot-Schutz-Umgehung, keine Abruf-Serien gegen dieselbe Domain, keine
  personenbezogenen Daten sammeln, die für die Aufgabe nicht gebraucht werden.

## Herkunft

Das hier ist die herausgelöste Recherche-Hälfte eines größeren persönlichen
Assistenten, entpersonalisiert und einzeln lauffähig gemacht. Deshalb sind die
Prompts und Skills auf Deutsch: sie sind so gewachsen, und übersetzen würde die
Formulierungen verwässern, an denen die Qualität hängt. Der Code ist englisch
benannt und ohne Deutschkenntnisse benutzbar.

Einzelne Skills bauen auf Vorarbeit anderer auf, jeweils in der `quelle:`-Zeile
im Frontmatter genannt:

- `web-scraping`: Muster nach [dumkydewilde, Ultimate Web Scraping](https://gist.github.com/dumkydewilde/97ab8337e30ca09c52b25343adf2aae1)
  und [Scrapfly, How to Scrape Hidden APIs](https://scrapfly.io/blog/posts/how-to-scrape-hidden-apis)
- `deep-research`: adaptiert aus daymade/claude-code-skills (MIT)
- `quellenarbeit`: Validierungslogik adaptiert aus K-Dense-AI/claude-scientific-writer (MIT)
- `archiv-recherche` und `seiten-index`: eigenständig, gegen die
  [Wayback CDX API](https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md)
  praktisch geprüft

Das Skill-Prinzip selbst (Index im Prompt, Volltext bei Bedarf nachladen)
stammt von den Anthropic Agent Skills.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
