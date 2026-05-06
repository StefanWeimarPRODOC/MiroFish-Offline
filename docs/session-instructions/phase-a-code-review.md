# Phase A — Code-Review-Briefing

> Erstellt: 2026-05-06 — gedacht als Briefing für eine Review-Session, die nach der Phase-A-Implementierung läuft, aber **vor** dem ministral-Test-Run.
> Zugehörige Implementierungs-Anleitung: [phase-a-quick-wins.md](phase-a-quick-wins.md)

## Kontext

Phase A umfasst vier Quick-Win-Fixes als Vorbereitung auf den nächsten Test-Run (ministral-3:14b mit ausführlichen deutschen Seed-Dokumenten):

- **MIR-26** Ollama Modell-Eviction → `keep_alive: 30m` pro LLM-Request
- **MIR-27** Persona-Routing-Heuristik für Custom Entity-Types
- **MIR-31** Cypher-Label-Sanitize: normalisieren statt rejecten
- **MIR-25** `requestWithRetry`: 4xx-Status nicht retryen

Die Implementierung lief in einem separaten Chat. Dieses Briefing dient dem Review **vor dem Merge in `main`** und **vor dem Test-Run**, weil Bugs in dieser Phase den Test verfälschen würden.

## Scope

Nur der **Diff dieser Phase-A-Branch gegen `main`**. Vorgängige MIR-23/MIR-24-Commits (b0f5d07) sind bereits gereviewt und nicht im Scope.

```bash
# Annahme: Branch heißt sweimar/mir-26-phase-a-quickwins (oder ähnlich)
git fetch origin
git diff origin/main...HEAD -- backend/ frontend/
```

Erwarteter Diff-Umfang: **~150-250 Zeilen**, verteilt auf 5-6 Files.

## Kritische Files

| Datei | Tickets | Was im Diff erwartet wird |
|---|---|---|
| `backend/app/services/llm_client.py` | MIR-26 | `extra_body` um `keep_alive` erweitert; eventuell `Config.OLLAMA_KEEP_ALIVE`-Lookup |
| `backend/app/services/simulation_config_generator.py` | MIR-26 | gleiches Pattern wie llm_client.py — eigener OpenAI-Client |
| `backend/app/services/oasis_profile_generator.py` | MIR-26, MIR-27 | `keep_alive` (gleiches Pattern); zusätzlich Routing-Heuristik in `_is_individual_entity` / `_is_group_entity`, ggf. Default-Fallback in `_generate_profile_with_llm` |
| `backend/app/storage/neo4j_storage.py` | MIR-31 | `_sanitize_label()` umgeschrieben — normalisieren statt rejecten; eventuell Backtick-Logik in Aufruf-Stellen |
| `backend/app/config.py` | MIR-26 | Neue Config-Variable `OLLAMA_KEEP_ALIVE` mit Default `"30m"`, aus `.env` lesbar |
| `frontend/src/api/index.js` | MIR-25 | `requestWithRetry`: 4xx-Check vor dem Retry-Pfad |
| (optional) `backend/tests/...` | MIR-27, MIR-31 | Unit-Tests für die neuen Heuristiken/Sanitize-Funktion |
| (optional) `.env.example` | MIR-26 | `OLLAMA_KEEP_ALIVE=30m` als Beispiel-Eintrag |

## Review-Checkliste

### Korrektheit pro Ticket

#### MIR-26 — `keep_alive` pro Request
- [ ] Wert wird tatsächlich an Ollama durchgereicht (nicht innerhalb `options` falsch verschachtelt). Korrekt: `extra_body={"options": {...}, "keep_alive": "30m"}` — `keep_alive` ist auf gleicher Ebene wie `options`, NICHT innerhalb.
- [ ] Alle drei OpenAI-Client-Stellen (LLMClient, SimulationConfigGenerator, OasisProfileGenerator) angepasst — keine vergessen
- [ ] Wert ist konfigurierbar, nicht hardcoded — `Config.OLLAMA_KEEP_ALIVE` mit Default `"30m"`
- [ ] Bei Non-Ollama-Backends (LM Studio etc.) wird `keep_alive` weggelassen oder ignoriert (kein Crash)
- [ ] Cleanup: Falls Backend stoppt während ein Modell mit `keep_alive: 30m` läuft, läuft das Modell weiter — User erwartet das? (Memory laut Doku)

#### MIR-27 — Persona-Routing-Heuristik
- [ ] Substring-Matches sind case-insensitive (`entity_type.lower()` o.ä.)
- [ ] Kollidierende Substrings: Was passiert bei `Patient_Organization`? (sollte vermutlich Group dominieren — explizite Reihenfolge prüfen)
- [ ] Default-Fallback bei keinem Match: dokumentiert (Code-Comment mit Begründung)? Logger-Warning für unbekannte Types?
- [ ] Bestehende exakte Matches (`person`, `university`, ...) funktionieren weiterhin (Backwards-Compat)
- [ ] Tests decken alle relevanten Custom-Types aus dem letzten Run ab: `Diabetologist`, `KOLDiabetology`, `NovaSulinSalesRep`, `DiabetesPatient`, `Medication`, `Location`
- [ ] Edge-Case: `Medication` und `Location` sind weder Person noch Organisation — was ist der erwartete Default? (vermutlich Group für Medication, weil Medikament keine Person ist; Location ist evtl. komplett zu skippen)

#### MIR-31 — Label-Sanitize
- [ ] Backtick-Logik: Wenn die neue Funktion auch Sonderzeichen (Umlaute, Mixed-Lang) durchlässt, MÜSSEN die Aufrufer Cypher-Backticks setzen — sonst Cypher-Syntax-Error. Prüfen: ist das gemacht?
- [ ] Sicherer Default: ASCII-only mit Umlaut-Mapping (ä→ae) — dann sind keine Backticks nötig. Welche Variante wurde gewählt?
- [ ] Edge-Cases: leerer String, nur Sonderzeichen (z.B. "/"), Unicode-Whitespace, sehr lange Strings (>200 Zeichen — Cypher hat Limits)
- [ ] Cypher-Injection-Sicherheit: Ist die neue Funktion weiterhin sicher gegen Injection? (Regex sollte alles außer Buchstaben/Digits/Underscore eliminieren)
- [ ] Originale Labels für UI-Anzeige bewahrt? (Optional, aber wertvoll — wenn ja, separate Property `original_type` o.ä. im Node)

#### MIR-25 — `requestWithRetry` 4xx
- [ ] Status-Check vor Retry-Pfad: `error?.response?.status >= 400 && < 500` → throw, nicht retry
- [ ] Network-Errors (`error.response` undefined, weil Request gar nicht durchkam) werden weiterhin retried
- [ ] Timeouts (axios `ECONNABORTED`) werden weiterhin retried
- [ ] Console-Warning klar formuliert ("Client error, not retrying" vs. "Server error, retrying")
- [ ] Existierende Endpoints brechen nicht (alle anderen API-Calls die `requestWithRetry` nutzen)

### Cross-Cutting

- [ ] **Testabdeckung:** Mindestens MIR-27 und MIR-31 sollten Unit-Tests haben — beides ist reine Logik ohne externe Abhängigkeiten, also gut testbar. Wenn die Implementierung das übersprungen hat: rausstellen.
- [ ] **Dokumentation:** Wurde `.env.example` aktualisiert? Stehen die neuen Config-Variablen im README oder Setup-Guide?
- [ ] **Logging:** Bei MIR-27 sollte ein Warning für unbekannte Types kommen — das hilft beim Test-Run, neue Custom-Types zu erkennen.
- [ ] **Backwards-Compat:** Funktioniert die Pipeline noch mit den alten Upstream-Entity-Types (`student, person, university, ngo, ...`)?

### Architektur & Stil

- [ ] Neue Code-Patterns folgen den bestehenden im Repo (siehe Abschnitt 10.5 in `docs/technical-report-benchmark-2026-04.md`)
- [ ] Keine neuen Hardcoded-Werte wo Config besser wäre
- [ ] Keine `print()` statt `logger.info()`/`logger.warning()`
- [ ] Keine `# TODO`-Kommentare ohne Linear-Ticket-Verweis
- [ ] Commit-Messages: `Fixes MIR-XX` Magic-Word richtig gesetzt? Ein Ticket pro Commit empfohlen.

### Performance

- [ ] **MIR-26 Eviction-Verifikation idealerweise schon im PR:** Hat der Implementierer einen Smoke-Test gemacht (`watch ollama ps` während kleinem Pipeline-Lauf)? Wenn nicht — als Acceptance-Kriterium für Phase B aufnehmen.
- [ ] **MIR-27:** Heuristik-Performance vernachlässigbar (einfacher Substring-Match), keine Bedenken.

## Bekannte Risiken & Edge-Cases

1. **Ollama-API-Wechsel:** `keep_alive` ist offiziell dokumentiert, aber falls Ollama-Version <0.x das nicht akzeptiert, schlägt der Pipeline-Run fehl. Aktuell: Ollama 0.23.0. Akzeptanz seit 0.x.
2. **MIR-27 False Positives:** `Vorstandsvorsitzender` enthält kein Substring-Match → fällt als Individual durch (was korrekt ist). `Versicherungsverband` enthält `*verband*` → Group (korrekt). Unsichere Fälle: `Personenversicherung` (Person + Verband) — welches Substring matcht zuerst? Prüfen ob die Reihenfolge der Checks deterministisch ist.
3. **MIR-31 Cypher-Backticks:** Wenn die neue Funktion Umlaute durchlässt, ist eine versehentlich nicht-quotierte Stelle ein Crash. Mein Vorschlag: ASCII-only mit Umlaut-Mapping als sicherster Default.
4. **MIR-25 Stille 4xx:** Achtung — wenn das Backend versehentlich 400 statt 5xx wirft, schluckt der Frontend-Wrapper das jetzt sofort. Prüfen ob alle aktuellen Backend-Endpoints bei transienten Fehlern wirklich 5xx zurückgeben.

## Output des Reviews

Standard-Format wie für die `superpowers:code-reviewer`-Subagents:

- **Kurzer Review-Bericht** (Markdown): pro Ticket Findings mit Severity (Critical/High/Medium/Low), Datei:Zeile-Referenz, Empfehlung
- **Approval-Empfehlung:** approve / approve-with-comments / request-changes
- **Falls Critical/High Findings:** Implementierer fixt zuerst, Re-Review danach. Erst dann Merge in `main`.

## Nach erfolgreichem Review

1. Branch in `main` mergen (Squash-Merge oder Merge-Commit, je nach Repo-Stil)
2. Linear: MIR-25, MIR-26, MIR-27, MIR-31 → Done (durch `Fixes`-Magic-Words automatisch nach Push, falls korrekt getaggt)
3. Container-Rebuild: `docker compose up -d --build mirofish`
4. Test-Run-Vorbereitung (siehe Ende von [phase-a-quick-wins.md](phase-a-quick-wins.md)):
   - `.env`-Switch auf `ministral-3:14b-mirofish`
   - Deutsche Seed-Dokumente bereitlegen
   - Phase B starten

## Verwandt

- [phase-a-quick-wins.md](phase-a-quick-wins.md) — Implementierungs-Anweisung
- `docs/technical-report-benchmark-2026-04.md` Abschnitt 9.4 (Limitationen 10-16) — Hintergrund aller 7 Folge-Tickets
- `docs/technical-report-benchmark-2026-04.md` Abschnitt 10.5 — bestehende Code-Patterns (gegen die geprüft wird)
- `docs/linear-workflow.md` — Magic-Words in Commit-Messages
