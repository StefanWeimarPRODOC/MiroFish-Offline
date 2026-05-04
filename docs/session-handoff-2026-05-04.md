# Session-Handoff: MiroFish-Offline / Simulab (2026-05-04)

## Was wurde in den letzten Sessions erreicht (2026-04-21 bis 2026-05-04)

### Erledigte Tickets (13)
- **MIR-5**: Graph-Memory-Updater DI-Bug behoben
- **MIR-6**: Report-Agent Interview-Timeout-Pattern
- **MIR-7**: Chunker Wortgrenzen-Fix
- **MIR-8**: Vektor-Dimensionen konfigurierbar (Auto-Detection + Migration)
- **MIR-9**: Zeitzonen CET/Berlin
- **MIR-10**: Narrative-Mode Toggle (Neutral/Guided), editierbare Topics
- **MIR-11**: Auto-Export Reports
- **MIR-12**: Auto-Export Personas + Configs
- **MIR-13**: Dediziertes LLM-Call-Logging
- **MIR-14**: num_ctx in allen LLM-Call-Stellen
- **MIR-16**: Separates NER-Modell (phi4-mini-ner)
- **MIR-17**: Pipeline-Timing + Content-Quality-Evaluation
- **MIR-18**: Sprachsteuerung Phase 1+2 (OUTPUT_LANGUAGE + vue-i18n mit 429 Strings)
- **MIR-21**: Token-Counting über gesamte Pipeline
- **MIR-22**: Post-Length-Variation & Persona-Optimierung
- **Rebrand**: GUI-Schriftzug von "MIROFISH OFFLINE" zu "SIMULAB"

### Benchmark-Erkenntnisse (8 Runs durchgeführt)
- **Sweet Spot**: Qwen 2.5:32b Q4 mit MIR-22 + Quick-Wins (Quality Score 68.1, ~5h Pipeline)
- **Q4 schlägt Q8**: Q8-Quantisierung führt zu mehr Sprachdrift (8.8% non-EN bei 14b Q8 vs 0.6% bei 14b Q4)
- **Ohne Narrative Guidance besser**: Run ohne narrative_direction produzierte umfangreichsten Report (5.160 Wörter)
- Vollständige Daten in [docs/technical-report-benchmark-2026-04.md](technical-report-benchmark-2026-04.md)

## Offene Tickets (5) — Priorität für nächsten Sprint

### High Priority

#### MIR-23: Report-Agent Interview-Block + Concurrent-Lock
**Bug**, beobachtet 2026-05-01

Zwei verbundene Probleme:
1. **Interview-Tool blockiert nach Simulation-Ende**: Inkonsistente Statusprüfung — manche Pfade skippen graceful, andere lassen 15-Min-Timeouts laufen
2. **Parallele Reports**: Frontend lässt zweite Report-Generierung starten während erste läuft → Ollama-Konkurrenz, Timeouts

**Files:**
- `backend/app/services/report_agent.py` — `interview_agents` Tool: Status-Check vor LLM-Call
- `backend/app/api/report.py` — Vor `agent.generate_report()` prüfen ob Report mit Status `generating` für diese `simulation_id` existiert (409 Conflict)
- `frontend/src/components/Step4Report.vue` — Generate-Button disabled während Generierung

#### MIR-24: i18n Phase 3 — Verbleibende englische LLM-Outputs
**Bug**, beobachtet 2026-05-01

Trotz `OUTPUT_LANGUAGE=Deutsch` weiterhin englisch:
1. **LLM-Konfigurationsableitung** (Time/Event config Reasoning-Felder)
2. **Persona-Beschreibungen** (Detailed Persona — bio + persona)
3. **Initial Activation Sequence** (6 Posts)
4. **Hot Topic Tags** — sollten differenziert sein (Medizin-Fachbegriffe EN, descriptive DE)

**Files:**
- `backend/app/services/simulation_config_generator.py:655-725` — `_generate_event_config()` für initial_posts und hot_topics
- `backend/app/services/simulation_config_generator.py` — Reasoning-Felder in allen 9 Generation-Phasen
- `backend/app/services/oasis_profile_generator.py:649-679` (individual) und `:691-726` (group) — Persona-Prompts mit OUTPUT_LANGUAGE-Verstärkung

**Lösungsansatz** (siehe MIR-24 für Details):
- OUTPUT_LANGUAGE mehrfach und prominent in jedem Prompt wiederholen
- Bei jedem Feld einzeln: "in {OUTPUT_LANGUAGE}"
- Hot Topics: Differenzierungs-Anweisung (Fachbegriffe vs. descriptive)

### Medium Priority

#### MIR-19: Model Selection Guide & Complexity Matrix
- Benchmark-Datenbank aus `timing.json`/`content_evaluation.json` aller Runs
- Complexity-Metrik aus Seed-Text (Zeichen, Entity-Dichte)
- Empfehlungsmatrix: Seed-Komplexität → Modell + erwartete Dauer
- Frontend-Anzeige der Zeitschätzung vor Simulationsstart
- Datengrundlage liegt vor: 8 Runs in `backend/uploads/simulations/`

### Low Priority

#### MIR-20: Agent-Chat Fortschrittsanzeige
- Spinner/Typing-Indicator während Agent "nachdenkt" (2-3 Min bei 32b)
- Timeout abhängig von Modellgröße (14b: 60s, 32b: 180s)

#### MIR-15: Auto-Run Pipeline / Headless Mode
- Kurzfristig: Auto-Proceed nach Graph-Build
- Langfristig: Headless-Modus für Batch-Runs

## Wichtige Architektur-Erkenntnisse für die Bearbeitung

### Pipeline-Flow
```
Seed-Text → Chunking → NER → Knowledge Graph (Neo4j)
  → Persona-Generation (parallel 5x) → Config-Generation (9 Phasen)
  → OASIS Dual-Platform Simulation → Report-Agent (ReACT) → Agent-Chat (IPC)
```

### Stellschrauben
- **Persona-Länge**: `oasis_profile_generator.py:662` (aktuell 600-1200 Wörter)
- **Post-Length-Guidance**: `_get_post_length_guidance()` (Entity-Type-basiert)
- **Narrative Mode**: Frontend Toggle Neutral/Guided (MIR-10)
- **OUTPUT_LANGUAGE**: `.env` + alle LLM-Prompt-Templates
- **Modell**: `.env: LLM_MODEL_NAME` (aktuell: `qwen2.5:32b` Q4)

### MiroFish kontrolliert nicht
- Interne OASIS Agent-Logik (CAMEL-AI Framework)
- OASIS-System-Prompt-Formatierung
- Reihenfolge der Agent-Aktivierung pro Runde

MiroFish kontrolliert nur den **Input** (CSV/JSON Profiles, simulation_config.json, initial_posts).

### Empfohlenes Setup für Tests
```env
LLM_MODEL_NAME=qwen2.5:32b
NER_MODEL_NAME=phi4-mini-ner
EMBEDDING_MODEL=qwen3-embedding:0.6b-fp16
OUTPUT_LANGUAGE=Deutsch  # für i18n-Tests
```

Ollama-Parallelisierung (via launchctl):
```
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=3
```

## Bekannte Stolpersteine

### Container-Restart vs. Rebuild
- **Restart**: Code-Änderungen die per `docker cp` reinkopiert wurden gehen verloren
- **Rebuild**: `docker compose up -d --build mirofish` — neuer Image-Build, frische .env, alle Code-Änderungen
- **Wichtig**: Wenn `.env` geändert wird, Rebuild statt Restart, sonst zeigt `timing.json` falschen Modellnamen

### Model-Name in timing.json
- `Config.LLM_MODEL_NAME` wird beim Backend-Startup gecached
- Bei Container-Restart ohne Rebuild: alter Wert bleibt im Speicher

### npm Network Issues beim Build
- Manchmal timeoutet `npm ci` während Docker Build
- Lösung: Build wiederholen, Docker Desktop neustarten falls hartnäckig

### Persona-Längen-Diskrepanz
- 800/1200-Wort-Limit wird vom LLM nicht ausgeschöpft (typisch 200-250 Wörter)
- Wenn Personas zu kurz sind: Minimum-Hinweis "MUST be at least 400 words" verstärken
- Mehr Pflicht-Dimensionen im Prompt zwingen zu mehr Inhalt

## Linear-Workflow

- **Branch-Namen**: Linear schlägt vor (z.B. `sweimar/mir-23-report-agent-interview-tool-blockiert-nach-simulation-ende`)
- **Commit-Tags**: `Part of MIR-XX` (in Progress) oder `Fixes MIR-XX` (auf Done)
- **GitHub-Webhook**: Aktiv, verknüpft Commits automatisch mit Tickets

## Aktueller Git-Stand

- Branch: main, up-to-date mit origin
- Letzter Commit: `b9e6cbe` (MIR-21/MIR-13)
- Untracked: docs/session-handoff-2026-04-24.md, docs/superpowers/2026-04-27-mir-10-review-fixes.md, docs/technical-report-benchmark-2026-04.md, docs/session-handoff-2026-05-04.md (dieses Dokument)

## Empfohlener Vorgehensvorschlag für die nächste Session

1. **MIR-24 zuerst** (i18n Phase 3) — keine architektonischen Änderungen, nur Prompt-Tuning. Schneller Win.
2. **Test-Run** mit deutscher Oberfläche um MIR-24 Erfolg zu validieren
3. **MIR-23 dann** — Report-Agent Interview-Tool Status-Check (Code-Änderung) + Concurrent-Lock (mehr Aufwand)
4. **Test-Run** der Report-Generierung mit Concurrent-Lock-Test
5. Optional: MIR-19 mit den 8 vorhandenen Benchmark-Runs als Datenbasis

## Referenzen

- [docs/technical-report-benchmark-2026-04.md](technical-report-benchmark-2026-04.md) — Vollständiger Benchmark-Report, Architektur-Erkenntnisse, Kunden-Argumente
- [docs/i18n-audit.md](i18n-audit.md) — ~300 Strings, aktualisiert 2026-04-23
- [docs/session-handoff-2026-04-21.md](session-handoff-2026-04-21.md) — Stand nach MIR-5 bis MIR-18 Phase 1
- [docs/session-handoff-2026-04-24.md](session-handoff-2026-04-24.md) — MIR-22 + Quick-Wins
- [Linear: MiroFish-Offline Project](https://linear.app/prodoc-digital/project/mirofish-offline-fork)
