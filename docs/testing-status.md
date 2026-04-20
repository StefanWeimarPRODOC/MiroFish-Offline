# MiroFish-Offline: Testing & Logging Status

Stand: 2026-04-20, nach Baseline-Tests mit qwen2.5:14b, gemma4-direct und ministral-3:14b.

## Vorhandene Tests

### Automatisierte Tests
- **Keine.** `pyproject.toml:38-42` deklariert pytest/pytest-asyncio als dev-Dependencies, aber es gibt keine Testdateien, keine `conftest.py`, keine `pytest.ini`.
- **CI/CD:** `.github/workflows/docker-image.yml` — nur Docker-Image-Build, keine Test-Pipeline.
- **Frontend:** Keine Jest/Vitest/Cypress-Tests.

### Manuelle Test-Skripte
| Skript | Zweck |
|---|---|
| `backend/scripts/test_profile_format.py` | Validiert OASIS-Profilformate (CSV/JSON), 2 Test-Agenten, print-basiert |
| `backend/scripts/run_twitter_simulation.py` | Automatisierte Twitter-Simulation (Config-JSON als Input) |
| `backend/scripts/run_reddit_simulation.py` | Reddit-Simulation |
| `backend/scripts/run_parallel_simulation.py` | Parallele Twitter+Reddit-Simulation |

### Ad-hoc-Tests in dieser Session
- `curl` gegen `/v1/chat/completions` (LLM-Erreichbarkeit aus Container)
- `curl` gegen `/api/embed` (Embedding-Dimensionen prüfen)
- `curl` gegen `/api/report/chat` (Chat-Response-Struktur debuggen)
- `docker compose logs` + Monitor-Pattern für Live-Beobachtung
- `ollama run gemma4-direct "List 3 fruits."` (Thinking-Unterdrückung prüfen)

## Vorhandenes Logging

### Logger-Infrastruktur
- **Zentral:** `backend/app/utils/logger.py:30-108` — Rotation (10MB, 5 Backups), Debug→Datei, Info→Console
- **Named Logger:** `mirofish`, `mirofish.neo4j_storage`, `mirofish.graph_builder`, `mirofish.simulation_runner` etc.

### Was wird geloggt

| Bereich | Datei | Was geloggt wird | Was NICHT geloggt wird |
|---|---|---|---|
| **LLM-Client** | `llm_client.py` | Nichts (!) | Modell, Temperature, Timing, Token-Count, Antwortlänge, strip_thinking-Hits |
| **Graph-Build** | `graph_builder.py:197-235` | Chunk-Progress, Batch-Info, Timing pro Chunk | NER-Ergebnis-Details (Entities/Relations pro Chunk) |
| **NER/Embedding** | `neo4j_storage.py:71-292` | Schema-Warnungen, Embedding-Batch-Status | Vektor-Dimensionen, Embedding-Timing |
| **Simulation** | `simulation_runner.py` | Status-Übergänge, PID, Platform | Round-Details (welcher Agent, welche Action) |
| **Action-Logger** | `scripts/action_logger.py:1-306` | JSONL: Round-Events, Agent-Actions, Results, Success | Nur in Skript-Modus, nicht im API-Flow |
| **Config-Generator** | `simulation_config_generator.py` | Generierungs-Schritte, LLM-Retries, Agent-Zuweisungen | LLM-Prompt/Response-Inhalte |
| **Profile-Generator** | `oasis_profile_generator.py` | Graph-Suche, JSON-Parsing-Fehler, Progress | Persona-Qualitäts-Metriken |
| **Report-Agent** | `report_agent.py:35-97` | Dedizierter `ReportLogger` → `agent_log.jsonl`: Aktion, Stage, Section, Details | LLM-Call-Timing, Tool-Call-Dauer |

### Beobachtungen aus dieser Session
- **Graph-Build-Logging ist gut** — Chunk-Timing, Fehler-Retries, finale Node/Edge-Counts sichtbar
- **Simulation-Logging ist mager** — „simulation completed: total_rounds=20, total_actions=21" ohne Breakdown
- **LLM-Client-Logging fehlt komplett** — das ist die größte Lücke für Modell-Benchmarking
- **IPC-Timeouts werden sauber geloggt** (ERROR + Traceback)

## Lücken

### Kritisch für Modell-Vergleiche
1. **Kein LLM-Call-Logging** — ohne Timing/Token-Counts pro Call kein sauberes Benchmarking
2. **Kein Persona-Export** — generierte Persona-Texte nur im Speicher, nicht als vergleichbare Datei
3. **Kein Report-Export** — Sections liegen in `report_*/section_*.md`, aber kein gebündelter Export

### Fehlend für Automatisierung
4. **Kein Health-Check-Endpoint** (`/health` oder `/healthz`)
5. **Keine End-to-End-Tests** (Upload → Graph → Simulation → Report)
6. **Kein Metriken-Export** (Prometheus/OpenTelemetry)

### Fehlend für Debugging
7. **LLM-Request/Response nicht loggbar** — bei JSON-Parse-Fehlern sieht man nicht was das LLM geantwortet hat
8. **Embedding-Dimensionen nicht geloggt** — Vektor-Mismatch war nur durch Neo4j-Fehlermeldung erkennbar

## Empfehlung

**Reicht das Bestehende für einen Testlauf?**

**Ja, für manuelle Smoke-Tests.** Die Session hat gezeigt, dass der Graph-Build-Log + `docker compose logs` + Monitor-Pattern ausreicht, um:
- Chunk-Fehler zu erkennen (JSON-Retries, verlorene Chunks)
- Vektor-Probleme zu sehen (Neo4j-Warnungen)
- Simulation-Abschluss zu verifizieren (completed-Events)
- Report-Status zu verfolgen (Section-saved-Events)

**Nein, für systematisches Modell-Benchmarking.** Dafür brauchen wir:
1. **LLM-Debug-Logging (Linear: MIR-13)** — Timing, Token-Count, Modell pro Call → Pflicht vor dem nächsten Modell-Vergleich
2. **Auto-Export Report + Personas (Linear: MIR-11, MIR-12)** — ohne das kein reproduzierbarer Qualitätsvergleich

**Reihenfolge:** MIR-13 (Debug-Logging) → MIR-11/12 (Exports) → dann nächsten Modell-Test (z.B. Phi-4).
