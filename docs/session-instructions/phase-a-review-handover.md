# Phase A — Review-Handover für Phase-B-Planung

> Erstellt: 2026-05-06 — gedacht als Übergabe an den Chat, in dem die Phase-A-Umsetzung (MIR-25/26/27/31) geplant wurde, damit dieser jetzt den Phase-B-Plan (ministral-3:14b Test-Run) erstellen kann.
>
> Verwandt: [phase-a-code-review.md](phase-a-code-review.md) (Review-Briefing), [phase-a-quick-wins.md](phase-a-quick-wins.md) (Implementierungs-Anleitung)

## TL;DR

- **Review-Ergebnis:** `approve-with-comments`
- **Vor-Merge-Auflage erfüllt:** `_sanitize_label`-Unit-Test wurde im Review-Chat nachgereicht (28 Cases, alle grün via direkter Logik-Validierung)
- **Code ist Merge-fertig** — keine offenen Critical/High-Findings
- **Drei Folge-Tickets** für Linear (siehe unten), nicht-blockierend
- **Phase-B-Acceptance-Kriterien** stehen unten — die müssen in den Test-Run-Plan einfließen

## Was im Review-Chat passiert ist

1. Diff gegen `main` geprüft (8 Files, +228/-22, 4 Commits)
2. Alle vier Tickets gegen die Briefing-Checkliste geprüft, inkl. der vom Implementer self-flagged Punkte
3. Backend-4xx-Audit für MIR-25-Risk-Assessment durchgeführt: alle 4xx-Codes (400/404/409) im Backend sind Logik-Fehler, keine transienten — der MIR-25-Fix verschluckt keine retry-würdigen Fälle
4. **Korrektur am Phase-1-Explore-Bericht:** Der Explore-Agent hatte fälschlich gemeldet, `keep_alive` sei "innerhalb von `options` verschachtelt" — direktes Code-Lesen widerlegt das. Die Struktur ist korrekt (`keep_alive` parallel zu `options` in `extra_body`).
5. `_sanitize_label`-Test als pytest-File geschrieben: [backend/tests/test_neo4j_label_sanitize.py](../../backend/tests/test_neo4j_label_sanitize.py)
6. Logik validiert via inline-Pure-Python-Asserts (28/28 grün) — pytest läuft erst im Docker-Build

## Findings im Detail

### 🟢 Approved (keine Action nötig)

| Ticket | Befund |
|---|---|
| MIR-26 | Struktur korrekt, alle 3 Stellen konsistent, Config-driven, `.env.example` dokumentiert |
| MIR-27 | Substring/Suffix-Listen vollständig (inkl. Erweiterungen `researcher`, `scientist`, `agency`, `association`, `foundation`, `ltd`, `llc`), Default-Fallback mit Logger-Warning, 14 Test-Cases |
| MIR-31 | Diacritic-Map sauber, Word-Separator-Regex robust, Cypher-Injection-sicher, Backtick-Quoting an Aufruf-Stellen |
| MIR-25 | 4xx-Check korrekt, Network/Timeout retry weiterhin, Backend-Audit zeigt keine transienten 4xx-Endpoints |

### 🟡 Folge-Tickets (Linear, nicht-blockierend)

#### **MIR-32 (neu) — `keep_alive` von `num_ctx` entkoppeln**
- Ort: [backend/app/utils/llm_client.py:92](../../backend/app/utils/llm_client.py#L92), [simulation_config_generator.py:454](../../backend/app/services/simulation_config_generator.py#L454), [oasis_profile_generator.py:533](../../backend/app/services/oasis_profile_generator.py#L533)
- Problem: Aktuell wird `keep_alive` nur gesetzt, wenn auch `_num_ctx` truthy ist. Bei `OLLAMA_NUM_CTX=0` oder leer würde `keep_alive` entfallen. Praxisrelevanz gering (Default 8192), aber Code-Klarheit.
- Saubere Variante:
  ```python
  if self._is_ollama():
      extra_body = {"keep_alive": Config.OLLAMA_KEEP_ALIVE}
      if self._num_ctx:
          extra_body["options"] = {"num_ctx": self._num_ctx}
      kwargs["extra_body"] = extra_body
  ```
- Severity: Medium (Code-Klarheit, kein funktionaler Bug)

#### **MIR-33 (neu) — Substring-Kollision in MIR-27 dokumentieren oder regeln**
- Ort: [oasis_profile_generator.py:505-506](../../backend/app/services/oasis_profile_generator.py#L505-L506)
- Beobachtung im Phase-B-Test-Run: Treten Custom-Types wie `Patient_Organization` auf, die sowohl Individual- als auch Group-Substrings matchen? Aktuell dominiert Individual (weil zuerst geprüft).
- Wenn ja: Tie-Break-Regel einführen (z.B. "bei Underscore/Bindestrich-zusammengesetzten Types dominiert Group"). Wenn nein: Code-Comment, dass Individual-Dominanz bewusste Wahl ist.
- Severity: Medium (Beobachtung in Phase B, dann Entscheidung)

#### **MIR-34 (neu, optional) — Suffix-Edge-Cases dokumentieren**
- Ort: [oasis_profile_generator.py:188](../../backend/app/services/oasis_profile_generator.py#L188), [194](../../backend/app/services/oasis_profile_generator.py#L194)
- `INDIVIDUAL_SUFFIXES = ("ist",)` matcht auch `List`, `Tourist`. `GROUP_SUFFIXES` enthält 2-Char `"ag"` (matcht `Tag`, `Bag`). Im Custom-Ontology-Kontext aus dem letzten Run nicht aufgetreten, aber Code-Comment wäre hilfreich.
- Severity: Low (Doku-Issue)

### 📝 Briefing-Doku-Issue
Die Briefing-Tabelle in [phase-a-code-review.md](phase-a-code-review.md#kritische-files) gibt `llm_client.py` als `services/`-File an — tatsächlich liegt es in `backend/app/utils/`. Bei der nächsten Briefing-Erstellung beachten.

## Was nachgereicht wurde im Review-Chat

- **Neu:** [backend/tests/test_neo4j_label_sanitize.py](../../backend/tests/test_neo4j_label_sanitize.py) — 28 parametrized Cases:
  - 17 Normalisierungs-Cases (Diacritics, Separatoren, Leading-digit, Underscore-Edge)
  - 6 None-Return-Cases (None, empty, whitespace-only, only-unsafe-chars)
  - 4 Cypher-Injection-Safety-Cases
  - Logik validiert via direkter Asserts: 28/28 grün

Dieser Test wurde noch **nicht committed**. Empfehlung: vor dem Phase-B-Test-Run einen Commit `test: MIR-31 — add unit tests for _sanitize_label` erstellen, dann Phase-A-Branch in `main` mergen.

## Phase-B-Acceptance-Kriterien (für den Test-Run)

Diese drei Punkte müssen im Phase-B-Plan auftauchen:

1. **`ollama ps`-Verifikation für MIR-26**
   - Während des Pipeline-Runs in einem zweiten Terminal: `watch -n 2 ollama ps`
   - Erwartung: das LLM-Modell (`ministral-3:14b-mirofish`) bleibt zwischen LLM- und Embedding-Calls **geladen** (status `running`, nicht evictet)
   - Wenn das Modell trotzdem evictet wird, ist MIR-26 entweder nicht wirksam oder die `OLLAMA_KEEP_ALIVE`-Env-Var wird nicht ausgelesen — beides Anlass für Followup-Ticket.

2. **MIR-27 Custom-Type-Beobachtung**
   - Im Pipeline-Log nach `Unknown entity_type 'X'` Logger-Warnings suchen
   - Liste der real auftretenden Custom-Types sammeln, prüfen ob sich Substring-Kollisionen zeigen (siehe MIR-33)
   - Wenn `Medication`/`Location` defaulten zu Individual: laut User-Briefing ist das nicht ideal (`Location` sollte evtl. komplett geskippt werden) — dafür ggf. ein neues Ticket

3. **MIR-31 Label-Diversität**
   - Nach dem Pipeline-Run im Neo4j-Browser: `MATCH (n:Entity) RETURN DISTINCT labels(n)` — wieviele unterschiedliche Custom-Labels?
   - Erwartung: keine "Rejected unsafe Cypher label"-Warnings im Log; Labels wie `GKV_Verband`, `Mueller_Verein` etc. sollten als Knoten-Labels existieren

## Was *nicht* in Phase B gemacht werden muss

- Keine weiteren Code-Changes vor dem Test-Run nötig (Phase A ist Merge-fertig nach Test-Commit)
- Kein pytest-Setup (Test-File existiert, Logik validiert; pytest-Run kommt automatisch wenn pytest in `requirements-dev.txt` aufgenommen wird — separates Anliegen)
- Kein End-to-End-4xx-Test für MIR-25 (User-self-flagged akzeptabel; Backend-Audit bestätigt: kein Risiko)

## Empfohlene Schritt-Reihenfolge nach diesem Handover

1. **Im aktuellen Phase-A-Branch:** Test committen
   ```
   git add backend/tests/test_neo4j_label_sanitize.py
   git commit -m "test: MIR-31 — add unit tests for _sanitize_label"
   ```
2. **Linear:** Folge-Tickets MIR-32, MIR-33, MIR-34 anlegen (oder bestehende prüfen)
3. **Phase-A-Merge:** Branch in `main` mergen — MIR-25/26/27/31 werden via `Fixes`-Magic-Words automatisch auf Done gesetzt
4. **Phase-B-Plan erstellen** mit:
   - `.env`-Switch auf `ministral-3:14b-mirofish`
   - Deutsche Seed-Dokumente (Liste/Bereitstellung)
   - Test-Run-Protokoll mit den drei Acceptance-Kriterien oben als Mess-Punkte
   - Erwartete Beobachtungen pro Ticket dokumentieren (für `update-tech-report`-Skill nach dem Run)
5. **Container-Rebuild:** `docker compose up -d --build mirofish` (frischer Container mit neuem `keep_alive`-Code)
6. **Test-Run starten**
7. **Nach dem Run:** `update-tech-report`-Skill für `docs/technical-report-benchmark-2026-04.md`-Update aufrufen

## Kontext für den nächsten Chat

Der nächste Chat hat:
- Den Phase-A-Implementations-Plan (mit Code, Self-Flagging der Edge-Cases)
- Bereits Wissen über die deutschen Seed-Dokumente und ministral-3:14b
- Vermutlich auch [phase-a-quick-wins.md](phase-a-quick-wins.md) als Referenz

Was er jetzt zusätzlich braucht (dieses Dokument):
- Welche Findings das Review hatte und welche schon erledigt sind
- Welche drei Phase-B-Acceptance-Kriterien gemessen werden müssen
- Welche Folge-Tickets parallel laufen können (nicht-blockierend für Phase B)
