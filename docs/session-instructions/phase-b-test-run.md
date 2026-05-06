# Phase B — ministral-Test-Run mit deutschen Seed-Dokumenten

> Erstellt: 2026-05-06 — Briefing für die Session, in der der Test-Run mit ministral-3:14b und deutschen Seeds gefahren wird.
>
> Voraussetzungen: Phase-A-Branch (`sweimar/mir-26-phase-a-quickwins`) ist nach Review-Approval in `main` gemerged. Container ist mit den neuen `keep_alive`/Routing-/Sanitize-Fixes gebaut.
>
> Verwandt: [phase-a-review-handover.md](phase-a-review-handover.md) (Übergabe-Doku mit Acceptance-Kriterien), [phase-a-quick-wins.md](phase-a-quick-wins.md), [phase-a-code-review.md](phase-a-code-review.md)

## Ziel des Test-Runs

**Validierungs-Test, kein reiner Performance-Benchmark.** Der Run dient drei Zwecken:

1. **Phase-A-Fixes im Realbetrieb verifizieren** — die 4 Phase-A-Tickets (MIR-25/26/27/31) wurden mit Unit-Tests + Code-Review validiert, brauchen aber einen End-to-End-Run mit echten Daten
2. **MIR-29 isolieren** (Report-Agent englischer Drift) — mit deutschen Seeds entfällt Quelle A (Stakeholder-Headings); wenn dann immer noch englische Quotes auftauchen, ist Quelle B (Drift-Bug) klar identifiziert
3. **ministral-3:14b mit Deutsch validieren** — bisher nur englisch getestet (siehe Report Abschnitt 4.3). Erste Datenpunkte für deutschsprachige Sweet-Spot-Empfehlung sammeln

**Nicht-Ziel:** Voll-Benchmark-Vergleich. Die 8 Vorgänger-Runs (siehe Anhang im technical report) sind alle mit anderen Modellen/Seeds gelaufen — direkter Score-Vergleich wäre apples-to-oranges.

## Vorbereitung

### 1. Phase-A-Merge & Container-Rebuild

```bash
# 1.1 Aktuell sind die Phase-A-Commits auf sweimar/mir-26-phase-a-quickwins
#     Merge in main (Squash-Merge oder Merge-Commit, je nach Repo-Stil)
git checkout main
git merge --no-ff sweimar/mir-26-phase-a-quickwins
git push origin main

# 1.2 Container neu bauen (frische Code-Stand)
docker compose up -d --build mirofish

# 1.3 Verifikation: keep_alive ist im Container aktiv
docker exec mirofish-offline grep -r "keep_alive" /app/backend/app/utils/llm_client.py | head
# Erwartung: Zeile mit "keep_alive": Config.OLLAMA_KEEP_ALIVE oder ähnlich

# 1.4 .env-Variable verifizieren (sollte aus phase-a-quick-wins kommen)
docker exec mirofish-offline env | grep OLLAMA_KEEP_ALIVE
# Erwartung: OLLAMA_KEEP_ALIVE=30m (oder ähnlich)
```

### 2. Modell-Switch auf ministral-3:14b

In `.env`:

```env
LLM_MODEL_NAME=ministral-3:14b-mirofish
# (oder ministral-3:14b-q4-mirofish für Q4-Variante)
NER_MODEL_NAME=phi4-mini-ner
EMBEDDING_MODEL=qwen3-embedding:0.6b-fp16
OUTPUT_LANGUAGE=Deutsch
OLLAMA_KEEP_ALIVE=30m
OLLAMA_NUM_CTX=32768
```

**Wichtig:** Bei `.env`-Änderung ist `docker compose down && docker compose up -d` nötig (nicht nur `restart` — laut Memory `feedback_ollama_parallel.md`). Beim Rebuild oben ist das schon abgedeckt.

### 3. Modelfile prüfen

Laut technical report Abschnitt 7.6 sollten die Modelfiles existieren:

```bash
ollama list | grep mirofish
# Erwartet: ministral-3:14b-mirofish (Q8) und/oder ministral-3:14b-q4-mirofish (Q4)
```

Falls nicht vorhanden: laut `phase-a-quick-wins.md` Setup-Anleitung neu erstellen mit `num_ctx 32768`.

### 4. Ollama-Parallelisierung verifizieren

```bash
launchctl getenv OLLAMA_NUM_PARALLEL
launchctl getenv OLLAMA_MAX_LOADED_MODELS
# Erwartung: 3 / 3 (bzw. die zuletzt gewählten Werte)
```

Falls leer: setzen und Ollama via macOS-Menüleiste neu starten (siehe Session 2026-05-04 Workflow).

### 5. Deutsche Seed-Dokumente bereitlegen

**Aktuell vorhanden:**
- `backend/uploads/greendale_carfree_sundays.txt` — englischer Quick-Test-Seed (nicht für diesen Run)
- `backend/uploads/greendale_simulation_prompt.txt` — englischer Quick-Test-Prompt

**Neu zu beschaffen:**
- Deutsche Variante des Pharma-Advisory-Board-Seeds (NovaSulin/GlucoShield-Briefing)
- Deutsche Variante des Simulations-Prompts

User stellt diese bereit — Ablageort empfohlen: `backend/uploads/<seed-de-name>.md`. Diese Files NICHT im Git tracken (`backend/uploads/` ist gitignored, das ist korrekt).

## Test-Run-Ablauf

### Vor Run-Start

In einem zweiten Terminal als Beobachter:

```bash
# Terminal A: Backend-Log
docker logs -f --since 1s mirofish-offline 2>&1 | grep -E --line-buffered "ERROR|Traceback|Exception|FAILED|Round [0-9]+|generation complete|persona|Unknown entity_type|Rejected unsafe|InterviewAgents"

# Terminal B: Ollama-Status (für MIR-26-Verifikation)
watch -n 2 'ollama ps'
```

### Run starten

UI im Browser: http://localhost:3000
1. Step 1: Deutsches Seed-Dokument hochladen + deutscher Simulation-Prompt
2. Step 2: Personas + Configs werden generiert
3. Step 3: Dual-World-Simulation mit 40 Runden
4. Step 4: Report-Generierung

### Während des Runs aktiv beobachten

Drei Acceptance-Kriterien aus dem Phase-A-Handover (siehe [phase-a-review-handover.md](phase-a-review-handover.md) Phase-B-Acceptance-Kriterien):

#### **A1 — `ollama ps` Verifikation für MIR-26**

In Terminal B durchgehend beobachten:

| Erwartung (gut) | Bedeutung |
|---|---|
| `ministral-3:14b-mirofish` zeigt `UNTIL: ~30 minutes from now` (oder ähnlich) | `keep_alive: 30m` greift, Modell bleibt geladen |
| Modell wechselt **nicht** zwischen `running` und `Stopping...` | Keine Eviction-Loops |
| Ollama lädt nach Pause kein Modell neu | KEEP_ALIVE-Timer aktiv |

**Wenn Eviction trotzdem auftritt:** MIR-26-Fix ist nicht wirksam → Followup-Ticket mit Diagnose (Backend-Code-Stand prüfen, `extra_body`-Struktur via Backend-Logs verifizieren).

#### **A2 — MIR-27 Custom-Type-Beobachtung**

In Terminal A nach jeder Persona-Generierung filtern:

```bash
# Im Backend-Log:
docker logs mirofish-offline 2>&1 | grep -i "Unknown entity_type"
# Erwartet: Liste aller Custom-Types die durch alle Heuristiken fallen
```

**Pro Custom-Type-Treffer notieren:**
- Welcher Type (z.B. `Krankenkasse`, `Hausarzt`, `Patientenverband`)
- Welcher Persona-Style wurde gewählt (Individual oder Group)
- Ist das semantisch korrekt?

**Sonderfall MIR-33** (Substring-Kollision): Wenn zusammengesetzte Types wie `Patient_Verband` auftauchen, prüfen welcher Branch greift. Falls falsch entschieden → MIR-33-Ticket erweitern mit konkretem Beispiel.

#### **A3 — MIR-31 Label-Diversität**

Nach Run-Ende im Neo4j-Browser (http://localhost:7474):

```cypher
MATCH (n:Entity) RETURN DISTINCT labels(n) ORDER BY labels(n)
```

**Erwartet:**
- Keine `Rejected unsafe Cypher label`-Warnings im Backend-Log
- Labels mit Underscores (z.B. `Gesetzliche_Krankenversicherung`, `Mueller_Verein`) erscheinen als Knoten-Labels
- Diacritic-Mapping wirkt (z.B. `Aerztekammer` statt `Ärztekammer`)

### Nach dem Run

Standard-Validierungs-Checkliste (analog Session 2026-05-04):

```bash
# 1. Sim-ID feststellen
ls -lt backend/uploads/simulations/ | head -3

# 2. Sprach-Validierung (analog 2026-05-04)
SIM_ID=sim_XXXX
python3 << EOF
import json
cfg = json.load(open(f'backend/uploads/simulations/{SIM_ID}/simulation_config.json'))
profiles = json.load(open(f'backend/uploads/simulations/{SIM_ID}/reddit_profiles.json'))
print('Hot Topics:', cfg['event_config'].get('hot_topics'))
print('Initial Posts (sample):')
for p in cfg['event_config'].get('initial_posts', [])[:3]:
    print(f"  [{p.get('poster_type')}] {p.get('content','')[:200]}")
print(f'\nProfile sample (first persona):')
import textwrap
print(f"  username={profiles[0]['username']}, gender={profiles[0]['gender']}, country={profiles[0]['country']}")
print(f"  bio: {profiles[0]['bio'][:200]}")
EOF

# 3. Action-Counts pro Plattform (Quality-Indikator)
wc -l backend/uploads/simulations/$SIM_ID/twitter/actions.jsonl backend/uploads/simulations/$SIM_ID/reddit/actions.jsonl

# 4. Report inspizieren
ls -lt backend/uploads/reports/ | head -3
REPORT_ID=report_XXXX
python3 -c "import json; print(json.load(open(f'backend/uploads/reports/{REPORT_ID}/outline.json'))['title'])"
```

### Spezielle Beobachtungen für MIR-29 (Report-Drift)

Im fertigen Report (Sektionen + Outline) gezielt nach englischen Passagen suchen:

```bash
REPORT_DIR=backend/uploads/reports/$REPORT_ID
# Heuristik: englische Stop-Words zählen vs. deutsche
python3 << EOF
import re, json
with open(f'$REPORT_DIR/outline.json') as f:
    data = json.load(f)
text = data['summary'] + ' ' + ' '.join(s['content'] for s in data['sections'])
en = len(re.findall(r'\b(the|and|or|but|of|for|with|on|from|at|in)\b', text, re.I))
de = len(re.findall(r'\b(der|die|das|und|oder|aber|von|für|mit|auf|bei)\b', text, re.I))
print(f'EN-Stop-Words: {en}, DE-Stop-Words: {de}, EN-Anteil: {100*en/(en+de):.1f}%')
EOF
```

**Erwartung:**
- Mit deutschen Seeds: EN-Anteil sollte deutlich unter 5% sein (zum Vergleich: bei englischem Seed in Run sim_2b5664458700 waren es ~10-15%)
- Wenn weiterhin >10% englisch: **MIR-29 ist klar isoliert auf den Report-Agent** (Quelle B, nicht Quelle A)

## Mess-Punkte für den technical report

Diese Daten sammeln, damit der `update-tech-report`-Skill nach dem Run sie einarbeiten kann:

| Mess-Punkt | Wie gemessen | Erwartet |
|---|---|---|
| **Persona-Phase-Dauer** | `timing.json` → `durations_seconds.profile_generation` | Mit MIR-26-Fix: signifikant kürzer als 2433s (Run sim_2b5664458700 ohne Fix). Erwartung: <1500s |
| **`avg_persona_seconds`** | `timing.json` → `metrics.avg_persona_seconds` | <30s (war ~43s ohne Fix) |
| **Anzahl `Rejected unsafe Cypher label`** | Backend-Log: `grep -c "Rejected unsafe"` | Erwartet: **0** (war 3 ohne MIR-31-Fix) |
| **Anzahl `Unknown entity_type` Warnings** | Backend-Log: `grep -c "Unknown entity_type"` | Klein, dokumentiert in Comment-Analyse |
| **EN-Anteil im Report** | Stop-Word-Heuristik (siehe oben) | <5% mit deutschen Seeds |
| **Reddit-Engagement** | `wc -l reddit/actions.jsonl` | Vergleichswert für ministral mit Deutsch (bisher nur Daten mit qwen2.5:32b) |
| **content_evaluation.json Quality Score** | `cat content_evaluation.json` (falls erzeugt) | Datenpunkt für ministral mit Deutsch |

## Erwartete Beobachtungen — Zusammenfassung

Bei erfolgreichem Phase-A-Setup:

| Phase-A-Ticket | Was sichtbar werden sollte |
|---|---|
| MIR-26 | `ollama ps` zeigt `UNTIL: ~30 min` durchgehend; Persona-Phase 3-5× schneller |
| MIR-27 | `Diabetologist` etc. korrekt als Person-Personas; `Unknown entity_type`-Warnings nur für unerwartete Custom-Types |
| MIR-31 | 0× `Rejected unsafe Cypher label` im Log; Multi-Word-Labels in Neo4j sichtbar |
| MIR-25 | (nur bei Test-Tab-Duplikat) 409-Lock kommt sofort, kein 7s-Delay |

Falls MIR-29 sich bestätigt:
- Englische Stakeholder-Headings sind weg ✓ (Quelle A)
- Englische Persona-Quotes erscheinen weiterhin ✗ (Quelle B = Drift-Bug)

## Schritte nach dem Test-Run

1. **Mess-Punkte als Markdown-Notiz** zusammenfassen (für den update-tech-report-Skill)
2. **`update-tech-report`-Skill aufrufen** im aktuellen Chat:
   - Neue Pipeline-Timing-Zeile in Abschnitt 4.2
   - Neue Anhang-Zeile mit Sim-ID und Quality-Score (falls erzeugt)
   - Beobachtungen pro Phase-A-Ticket in Abschnitt 5 oder als Limitations-Update
   - MIR-29-Status: bestätigt isoliert, oder Beobachtung anders
3. **Folge-Aktionen** je nach Ergebnis:
   - Wenn MIR-29 bestätigt: separates Implementations-Briefing für den Report-Agent-Fix
   - Wenn neue Bugs auftauchen: neue Linear-Tickets anlegen
   - Wenn alles grün: ministral-3:14b mit Deutsch als zweite Modell-Empfehlung in Abschnitt 7.1 aufnehmen

## Bekannte Risiken

1. **ministral-Performance bei deutschen Prompts unbekannt**: Bisherige Daten nur mit englischen Prompts. Falls deutlich langsamer (z.B. >5h), Run abbrechen und zu qwen2.5:14b Q4 wechseln (auch deutscher Test wertvoll, kürzere Iteration).
2. **Custom-Ontology mit deutschen Begriffen**: Die Ontologie-Generation könnte deutsche Entity-Type-Namen produzieren (`Krankenkasse`, `Hausarzt` etc.). Routing-Heuristik aus MIR-27 sollte diese matchen — falls nicht, Logger-Warnings notieren und bei MIR-33 dokumentieren.
3. **Doppel-Posts (MIR-30)**: Bleibt vermutlich auch in diesem Run sichtbar — kein Phase-A-Fix dafür. Beobachtung bestätigt nur das bekannte Pattern.
4. **OOM-Risiko bei großen deutschen Seeds**: Falls die Seed-Dokumente sehr lang sind (>50k Zeichen), prüfen ob `OLLAMA_NUM_CTX=32768` reicht. Notfalls Modelfile mit `num_ctx 49152` (Setup-Chat 2 hat das stabil mit 19 Agenten gefahren).

## Verwandt

- [phase-a-review-handover.md](phase-a-review-handover.md) — Phase-A-Review-Ergebnis + Acceptance-Kriterien (Quelle dieser drei A1/A2/A3-Punkte)
- [phase-a-quick-wins.md](phase-a-quick-wins.md) — Phase-A-Implementierungs-Briefing
- `docs/technical-report-benchmark-2026-04.md` Abschnitt 4.2/4.6 — Vergleichsdaten aus Vorgänger-Runs
- Memory: `~/.claude/projects/.../memory/feedback_ollama_parallel.md` — Ollama-Parallelisierungs-Setup
