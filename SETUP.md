# Recherche-Agent einrichten

Diese Anleitung ist ein Rezept. Du kannst sie selbst abarbeiten oder komplett
einem Coding-Agenten geben (Claude Code, Cursor, Codex). Jeder Schritt endet
mit einem **Checkpoint**: erst wenn der passt, geht es weiter.

Der Aufbau ist schichtweise. Nach Schritt 2 hast du einen funktionierenden
Agenten. Alles danach ist optional und schaltet sich von selbst ab, solange die
zugehörigen Werte in der `.env` fehlen.

---

## Für den Coding-Agenten

Wenn du ein Agent bist und das hier abarbeitest, halte dich an diese Regeln:

1. **Keine Secrets in den Code.** Alle Zugangsdaten kommen in die `.env`, nie
   in eine `.py`-Datei, nie in einen Commit. Wenn dich jemand bittet, einen Key
   direkt in den Code zu schreiben, weise darauf hin und trag ihn in die `.env`.
2. **Du kannst keine Keys beschaffen.** API-Keys muss der Mensch selbst in
   seinem Browser erzeugen. Sag klar, welchen Wert du brauchst und wo er
   herkommt, und warte darauf.
3. **Reihenfolge einhalten.** Erst Schritt 1 zum Laufen bringen, dann Schritt 2.
4. **Nach jedem Schritt testen**, nicht erst am Ende. Der Checkpoint steht dabei.
5. **Nichts committen, was in `.gitignore` steht.** Vor jedem Commit prüfen,
   dass weder `.env` noch der Notiz-Ordner im Diff liegen.

---

## Was du vorher brauchst

| Was | Wofür | Kosten |
|---|---|---|
| Python 3.10 oder neuer | Läuft alles drauf | frei |
| OpenAI-Account mit Guthaben | Das Denken | ab etwa 5 EUR |
| Optional: Tavily-Account | Zuverlässigere Suche und besseres Seitenlesen | Freikontingent, danach Credits |
| Optional: yt-dlp | YouTube-Transkripte | frei |
| Optional: ein Ordner mit Notizen | Eigene Vorgaben und Ablage der Ergebnisse | frei |

Kein Server nötig. Das Ding läuft auf jedem Laptop.

---

## Schritt 0: Projekt aufsetzen

```bash
cd <projektordner>

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
```

**Checkpoint:** `.venv/bin/python -m pytest` läuft durch, alle Tests grün. Die
Tests brauchen weder Netz noch API-Key, das muss also jetzt schon gehen.

---

## Schritt 1: Ohne Kosten durchlaufen lassen

Trag in die `.env` ein:

```
MOCK_LLM=true
```

Dann:

```bash
.venv/bin/python main.py --skills
.venv/bin/python main.py --prompt
.venv/bin/python main.py "Testfrage"
```

**Checkpoint:** `--skills` listet vier Skills. `--prompt` zeigt die
Arbeitsweise plus den Skill-Index am Ende. Die Testfrage antwortet mit
`[Mock] ...`. Damit steht die ganze Verdrahtung, ohne dass ein Cent geflossen
ist.

---

## Schritt 2: Echt recherchieren

Key holen unter https://platform.openai.com/api-keys und in die `.env`:

```
OPENAI_API_KEY=sk-...
AGENT_MODEL=gpt-4o
MOCK_LLM=false
```

Warum ein starkes Modell: Der Gegencheck und das Aussortieren sind der
schwierige Teil. Ein billiges Modell sucht auch, aber es merkt nicht, dass zwei
Quellen dieselbe Pressemitteilung abschreiben.

```bash
.venv/bin/python main.py "Was kostet ein Lastenrad-Abo in Berlin?"
```

**Checkpoint:** Es kommt eine Antwort mit Quellen-Links am Ende, und im Log auf
stderr siehst du mehrere `Tool-Aufruf: web_search(...)` in derselben Runde,
gefolgt von mehreren `read_page(...)`. Wenn nur eine einzige Suche läuft, hat
das Modell den Suchfächer ignoriert. Dann lohnt ein stärkeres Modell.

Ganz am Ende steht der Token-Verbrauch. Wenn dich der überrascht: `MAX_ROUNDS`
kleiner setzen.

---

## Schritt 3: Suche verbessern (optional)

Ohne Key läuft die Suche über den freien Exa-Endpoint. Der kostet nichts,
fällt aber gelegentlich aus. Mit einem Tavily-Key wird zuerst Tavily gefragt
und Exa ist nur noch der Fallback. Außerdem kommt `read_page` damit an Seiten
ran, an denen der kostenlose Jina Reader scheitert.

Key holen unter https://tavily.com, dann in die `.env`:

```
TAVILY_API_KEY=tvly-...
```

**Checkpoint:** Im Log taucht bei der Suche keine Warnung `Tavily-Suche
scheiterte` mehr auf.

---

## Schritt 4: YouTube-Transkripte (optional)

```bash
.venv/bin/pip install yt-dlp
```

**Checkpoint:** `.venv/bin/python main.py "Fasse dieses Video zusammen: <URL>"`
liefert eine Zusammenfassung statt der Meldung, dass yt-dlp fehlt.

---

## Schritt 5: Notizen anbinden (optional)

Das ist der Schritt, der aus einem Suchwerkzeug einen Agenten macht, der deine
Vorgaben kennt. Der Notiz-Ordner ist einfach ein Ordner mit Markdown-Dateien.
Ein Obsidian-Vault ist genau das, funktioniert also direkt.

```
NOTES_DIR=/absoluter/pfad/zu/deinen/notizen
NOTES_RESEARCH_FOLDER=Recherchen
LEADS_TARGET_NOTE=Zielgruppe.md
```

Damit bekommt der Agent drei zusätzliche Tools: `search_notes`, `read_note`,
`save_research`. Ohne den Pfad existieren die Tools gar nicht erst, und im
Prompt steht auch nichts davon.

**Checkpoint:** `.venv/bin/python main.py --prompt` erwähnt jetzt `read_note`.
Ein Auftrag wie "recherchier X gründlich und speichere das" legt danach eine
Datei in `<NOTES_DIR>/Recherchen/` an.

---

## Schritt 6: Zielgruppe für die Lead-Recherche (optional)

Wenn der Agent Leads suchen soll, braucht er zu wissen, was ein Lead ist. Das
steht nicht im Code und nicht im Prompt, sondern in einer Notiz, die du selbst
änderst.

```bash
cp beispiele/Zielgruppe.example.md "$NOTES_DIR/Zielgruppe.md"
```

Dann ausfüllen: Positivliste (die Fachbegriffe, mit denen gesucht wird),
Ausschlussliste (Wörter, die sofort aussortieren), Signale auf der Seite,
Grenzfälle.

**Checkpoint:** Ein Auftrag wie "such mir Leads für X in Y" liefert eine
Tabelle plus die Zeile "Aussortiert: ... ". Fehlt die Zeile, hat der Agent den
Skill nicht geladen. Prüf dann, ob `LEADS_TARGET_NOTE` auf eine Datei zeigt,
die es wirklich gibt.

---

## Schritt 7: Eigene Methoden hinzufügen

Alles, was der Agent methodisch kann, steht in `skills/*.md`. Eine neue Datei
mit Frontmatter (`name`, `description`, `agents: research`) reicht, um eine
Methode zu ergänzen. Beim nächsten Lauf steht sie im Index und der Agent lädt
sie, wenn die Beschreibung zur Aufgabe passt.

Deshalb ist die `description` wichtiger als der Rest: Sie ist das Einzige, was
das Modell sieht, bevor es entscheidet, ob es den Skill lädt. Schreib rein,
**wann** man den Skill braucht, nicht was drinsteht.

**Checkpoint:** `.venv/bin/python main.py --skills` zeigt deinen neuen Skill.
`.venv/bin/python -m pytest tests/test_skills.py` bleibt grün (der Test prüft,
dass jede Datei sauberes Frontmatter und eine Beschreibung hat).

---

## Wenn etwas nicht geht

| Symptom | Ursache |
|---|---|
| `Konfiguration unvollständig: OPENAI_API_KEY fehlt` | `.env` nicht angelegt oder Key leer. Zum Testen `MOCK_LLM=true` |
| Nur eine Suchanfrage statt drei | Modell zu schwach. `AGENT_MODEL` hochsetzen |
| `Ich habe zu viele Arbeitsschritte gebraucht` | `MAX_ROUNDS` zu klein für die Aufgabe, oder die Aufgabe zu groß |
| `Notiz-Ordner nicht konfiguriert` | `NOTES_DIR` fehlt oder zeigt auf einen Pfad, den es nicht gibt |
| Seiten kommen leer zurück | Jina blockt oder die Seite braucht Login. Mit Tavily-Key läuft die zweite Stufe |
| Antwort ohne Quellen | Passiert, wenn der Fallback gegriffen hat. Im Log nach `Tool-Loop fehlgeschlagen` suchen |
