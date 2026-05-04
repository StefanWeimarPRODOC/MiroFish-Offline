# Simulab: Technischer Report — Benchmark, Optimierung & Einsatzszenarien

> April/Mai 2026 | PRODOC Digital GmbH
> Projektname intern: MiroFish-Offline → **Simulab**

---

## 1. Executive Summary

**Simulab** (ehemals MiroFish-Offline) ist eine Multi-Agent Social-Media-Simulationsplattform, die vollständig lokal auf Apple Silicon läuft. Sie verwandelt unstrukturierte Dokumente in realistische Social-Media-Szenarien: Aus einem Seed-Text (z.B. ein Pharma-Launch-Briefing) werden automatisch Stakeholder-Personas erstellt, die dann auf simulierten Twitter- und Reddit-Plattformen interagieren. Ein Report-Agent analysiert die Ergebnisse und erstellt eine Vorhersage-Analyse.

**Einsatzszenarien:**
- Pharma-Launch-Message-Testing vor echten Advisory Boards
- Stakeholder-Reaktionsvorhersage auf politische Entscheidungen
- Krisenmanagement-Simulation (Was passiert wenn Nachricht X öffentlich wird?)
- Meinungsdynamik-Forschung (Wie verbreiten sich Narrative in sozialen Netzwerken?)
- Workshop-Begleitung (Simulation als Diskussionsgrundlage)
- Markenpositionierung und Competitive Intelligence

**Kernversprechen:** 100% lokal, keine Cloud-APIs, keine Daten verlassen die Maschine. Läuft auf einem Mac Studio mit 128 GB RAM in 3-5 Stunden pro Simulation.

### 1.1 Upstream-Herkunft und Anpassungen

Simulab basiert auf [nikmcfly/MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline), einem Fork von [666ghj/MiroFish](https://github.com/666ghj/MiroFish). Das Original (666ghj) ist für den **chinesischen Markt** entwickelt und benötigt Cloud-APIs (DashScope, Zep Cloud) — für lokalen Offline-Betrieb nicht geeignet. Der nikmcfly-Fork hat die Migration auf Neo4j + Ollama durchgeführt und das UI ins Englische übersetzt. Simulab baut darauf auf und fügt deutsche Sprachsteuerung, Pipeline-Optimierungen und Benchmark-Infrastruktur hinzu.

**Fork-Hierarchie:** `666ghj/MiroFish` → `nikmcfly/MiroFish-Offline` (Offline-Migration) → `StefanWeimarPRODOC/MiroFish-Offline` (Simulab)

Das Original nutzte Zep Cloud für Embeddings, DashScope für LLM-Inferenz und war auf chinesische Arbeitszeiten (Beijing Time) ausgelegt.

Für den lokalen Einsatz in Deutschland wurden folgende Anpassungen vorgenommen:

| Bereich | Original (China) | Anpassung (Deutschland) |
|---------|------------------|------------------------|
| **LLM-Backend** | DashScope (Cloud) | Ollama (lokal, Apple Silicon) |
| **Embeddings** | Zep Cloud | Ollama (`qwen3-embedding:0.6b-fp16`) |
| **Arbeitszeiten** | Beijing Time (Peak 19-22 Uhr) | CET/CEST (Peak 18-21 Uhr, Feierabend-Pattern) |
| **Sprache** | Chinesisch/Englisch | Deutsch (Reports, Personas, UI via vue-i18n) |
| **Default-Land** | US/CN | DE |
| **UI** | Chinesisch | Englisch + Deutsch (Sprach-Selector) |

Die Zeitzonen-Umstellung betrifft die gesamte Simulationskonfiguration: Activity-Multiplier, Peak-/Off-Peak-Hours, Default-Zeitkonfiguration und alle LLM-Prompts die Arbeitszeiten referenzieren (`simulation_config_generator.py`). Die Sprachsteuerung wurde in zwei Phasen implementiert: Phase 1 setzte `OUTPUT_LANGUAGE` in allen LLM-Prompts, Phase 2 führte vue-i18n mit 429 Strings (EN/DE) im Frontend ein (MIR-18).

---

## 2. Projekt-Fortschritt: Ticket-Übersicht

### 2.1 Erledigte Tickets (13 von 18)

#### Kritische Bugs behoben

| Ticket | Titel | Was wurde gemacht |
|--------|-------|-------------------|
| MIR-5 | Graph-Memory-Updater DI-Bug | `storage`-Parameter in `start_simulation()` durchgereicht. Graph-Memory-Updates waren zuvor stumm deaktiviert. |
| MIR-6 | Report-Agent Interview-Timeout | IPC-Timeout von 180s auf robustes Retry-Pattern umgestellt. Report-Sections fallen nicht mehr auf Force-Generate zurück. |
| MIR-7 | Chunker splittet mitten im Wort | `rfind(' ')`-Fallback in `file_parser.py` implementiert. Verhindert Wortfragmente als Graph-Entities. |

#### Simulationsqualität verbessert

| Ticket | Titel | Was wurde gemacht |
|--------|-------|-------------------|
| MIR-22 | Post-Length-Variation & Persona-Optimierung | Persona-Wort-Limit auf 600-1200 erhöht. 9 Pflicht-Dimensionen pro Persona (inkl. Example Quotes, Known Objections, Boundaries). Post-Length-Guidance pro Entity-Type. Emoji/Hashtag-Dämpfung. Quality Score: 26→68.1. |
| MIR-10 | Config-Generator Bias reduzieren | Narrative Direction → Discussion Topics (neutral). Frontend-Toggle Neutral/Guided. Editierbare Topics. Initial Posts mit Poster-Type-Badges. Emergente Dynamik statt Self-Fulfilling Prophecy. |
| MIR-9 | Agent-Aktivitätszeiten | Von chinesischen auf deutsche Zeitzonen (CET/CEST) umgestellt. |

#### Infrastruktur & DX

| Ticket | Titel | Was wurde gemacht |
|--------|-------|-------------------|
| MIR-8 | Vektor-Dimensionen konfigurierbar | Auto-Detection der Embedding-Dimensionen beim Start. Automatische Migration bei Modellwechsel (Index Drop + Rebuild, kein Volume-Löschen nötig). `.env`-Override via `EMBEDDING_DIMENSION`. |
| MIR-16 | Separates NER-Modell | `NER_MODEL_NAME` in `.env` konfigurierbar. phi4-mini-ner (3.3 GB) statt Haupt-LLM (17-33 GB) für NER. GPU-Konkurrenz eliminiert. |
| MIR-14 | num_ctx in allen LLM-Call-Stellen | `extra_body` mit `num_ctx` in allen 3 OpenAI-Client-Stellen durchgereicht. |
| MIR-17 | Pipeline-Timing persistent | `timing.json` + `content_evaluation.json` automatisch pro Run. Phasen-Timing, Content-Qualitätsmetriken, Quality Score. |
| MIR-11 | Auto-Export Report | Report nach Generierung automatisch als gebündeltes MD in `backend/uploads/`. |
| MIR-12 | Auto-Export Personas + Configs | Alle Persona-Texte + Activity-Configs als JSON exportiert. Persona-Qualität zwischen Modellen vergleichbar. |

#### Internationalisierung

| Ticket | Titel | Was wurde gemacht |
|--------|-------|-------------------|
| MIR-18 | Sprachsteuerung & i18n | Phase 1: `OUTPUT_LANGUAGE` in allen LLM-Prompts. Phase 2: vue-i18n mit 429 Strings (EN/DE), Sprach-Selector im UI mit localStorage-Persistenz. Fremdsprach-Drift von 8.8% auf 0.0% reduziert. |

#### Observability & Logging

| Ticket | Titel | Was wurde gemacht |
|--------|-------|-------------------|
| MIR-21 | Token-Counting Pipeline | `response.usage` aus allen LLM-Calls ausgelesen, pro Phase aggregiert (profile_generation, config_generation), in `timing.json` gespeichert. `LLMClient.record_usage()` als öffentliche API für externe Caller. |
| MIR-13 | LLM Call Logging | Dedizierte Log-Datei `llm-calls-YYYY-MM-DD.log` mit Per-Call-Metriken (Modell, Temperature, Duration, Tokens, Thinking-Stripped). `propagate=False` hält Debug-Output aus dem Haupt-Log, Warnings gehen weiterhin an Console. |

### 2.2 Offene Tickets (3)

| Ticket | Titel | Prio | Beschreibung |
|--------|-------|------|-------------|
| MIR-19 | Model Selection Guide | Medium | Benchmark-Datenbank, Complexity-Matrix (Seed-Metriken → Modell-Empfehlung), automatische Seed-Analyse. |
| MIR-20 | Agent-Chat Fortschrittsanzeige | Low | Spinner/Typing-Indicator während Agent "nachdenkt" (2-3 Min bei 32b-Modellen). |
| MIR-15 | Auto-Run Pipeline / Headless Mode | Low | Kurzfristig: Auto-Proceed nach Graph-Build. Langfristig: Vollständiger Headless-Modus für Batch-Runs. |

---

## 3. Gefundene Probleme & durchgeführte Lösungen

### 3.1 Kritische Bugs

| Problem | Ursache | Fix | Ticket |
|---------|---------|-----|--------|
| **OOM-Crash bei >60 Agents** (Runde 11-14) | 2000-Wort-Personas als System-Prompt bei jedem LLM-Call; Docker VM nur 7.6 GB | Persona-Limit auf 600-1200 Wörter; Docker VM auf 32 GB; separates NER-Modell (3.3 GB statt 28 GB) | MIR-5, MIR-16 |
| **Report-Generierung schlug fehl** | Python `.format()` interpretierte JSON-Beispiel `{"title": ...}` als Format-Variable | Geschweifte Klammern im Prompt-Template escaped (`{{` statt `{`) | MIR-18 |
| **Graph-Memory-Updater stillgelegt** | DI-Bug: `storage` Parameter fehlte in `start_simulation()` | Storage über Flask DI durchgereicht | MIR-5 |
| **Chunker zerschnitt Wörter** | `file_parser.py` splittet nach fester Zeichenzahl ohne Wortgrenzen | `rfind(' ')` Fallback implementiert | MIR-7 |
| **Report-Agent Chat rendert nicht** | Backend liefert `{response: {response: "...", sources: [], tool_calls: []}}`, Frontend erwartet String → `[object Object]` oder leere Anzeige | `Step5Interaction.vue:697-700`: Response-Objekt unwrappen (`typeof raw === 'object' ? raw.response : raw`) | pre-ticket |
| **Benchmark-Daten nie geschrieben** | `state.total_actions_count` existierte nicht als Dataclass-Attribut → stiller AttributeError | Ersetzt durch `state.twitter_actions_count + state.reddit_actions_count` | MIR-17 |
| **Leere LLM-Antworten bei großen Prompts** | `OLLAMA_NUM_CTX` Default 8192 zu klein für MiroFish-Prompts (Ontologie-Prompt 5628 + Dokument 11512 = ~17k chars). Ollama truncierte den Prompt stillschweigend → leere Antworten nach ~60s. | `OLLAMA_NUM_CTX=32768` in `.env` + Modelfile mit `PARAMETER num_ctx 32768` | pre-ticket → MIR-14 |
| **Ollama alloziert 262k Context (59 GB RAM)** | Ollama lädt Modelle mit dem Default-Context des Modells (Ministral: 262k), nicht mit dem per `extra_body` angeforderten `num_ctx`. KV-Cache für 262k Tokens bei 14B Q8 = ~44 GB. Diagnose via `ollama ps`. | Modelfile mit festem `PARAMETER num_ctx 32768` → 21 GB statt 59 GB | pre-ticket → 7.5 |
| **Neo4j Vektor-Dimensions-Mismatch** | `qwen3-embedding` erzeugt 1024d-Vektoren, aber Neo4j-Index war mit 768d (nomic-embed-text) angelegt. Hybrid-Search Vektorkomponente fiel stumm aus (nur BM25-Fallback). Quantifizierter Impact: mit BM25-only 10-11 Fakten und **1 related Node** pro Agent; mit korrektem 1024d-Index **23 Fakten und 39 related Nodes** pro Agent. | `docker compose down -v` zum Reset; langfristig Auto-Detection (MIR-8) | pre-ticket → MIR-8 |
| **Docker OOM bei Dual-World-Simulation** | Docker Desktop Default-Memory-Limit ~7.6 GB. Bei 53 Agenten × 2 Plattformen (Twitter+Reddit) parallel → SIGKILL (Exit Code -9) in Runde 7-12. | `deploy.resources.limits.memory: 32g` in `docker-compose.yml` | pre-ticket |

### 3.2 Architektur-Verbesserungen

| Problem | Erkenntnis | Lösung | Ticket |
|---------|------------|--------|--------|
| **Fremdsprach-Posts** (Chinesisch, Thai) | Qwen-Modelle driften in andere Sprachen, besonders Q8-Quantisierung | `OUTPUT_LANGUAGE=English` in allen Prompts + vue-i18n Frontend + Sprach-Selector | MIR-18 |
| **Config-Generator Bias** | `narrative_direction` gibt Simulations-Ergebnis vorweg → Self-Fulfilling Prophecy | Neutral/Guided Toggle, editierbare Discussion Topics, neutrale Prompt-Formulierung | MIR-10 |
| **Posts zu gleichförmig** | Alle Posts 25-45 Wörter, StdDev nur 7-14; in Realität 3-280 Zeichen | Post-Length-Guidance pro Entity-Type; Persona um Communication Style, Example Quotes, Boundaries erweitert | MIR-22 |
| **Emoji/Hashtag-Explosion** | Personas ermutigten zu viel "Social Media Verhalten" | Explizite Dämpfung: "max 1-2 emojis, max 2 hashtags per post" | MIR-22 |
| **Embedding-Modellwechsel zerstörerisch** | Hardcoded 1024d, Neo4j-Volume musste gelöscht werden | Auto-Detection + automatische Migration (Index Drop/Rebuild ohne Datenverlust) | MIR-8 |
| **Kein Performance-Tracking** | Pipeline-Zeiten nur in Container-Logs, gehen bei Restart verloren | `timing.json` + `content_evaluation.json` automatisch pro Run | MIR-17 |
| **3 separate LLM-Call-Stellen** | `llm_client.py` (zentral), `simulation_config_generator.py` und `oasis_profile_generator.py` (eigene OpenAI-Clients). Konfigurationsänderungen (num_ctx, think, extra_body) mussten an 3 Stellen repliziert werden. | `extra_body` mit `num_ctx` in allen 3 Stellen durchgereicht | pre-ticket → MIR-14 |
| **Kein LLM-Debug-Logging** | LLM-Calls nur über Ollama-Server-Logs (`~/.ollama/logs/server.log`) sichtbar, die keine Prompts/Antworten zeigen. Fehlerdiagnose bei leeren Antworten extrem erschwert. | Request/Response-Logging im `LLMClient`: Modell, Timing, Antwortlänge (raw vs clean), ob Thinking-Tags gestrippt wurden | pre-ticket → MIR-13 |

### 3.3 Security & Code-Quality Review

Ein vollständiger Codebase-Review wurde mit 8 parallelen Review-Agents durchgeführt (3 Perspektiven: Security, Code Quality, Efficiency). Scope: nur localhost-relevante Befunde, Netzwerk-/Auth-Issues wurden bewusst ausgeschlossen da Simulab ausschließlich lokal läuft.

#### Umgesetzte Security-Fixes

| Befund | Schwere | Fix | Commit |
|--------|---------|-----|--------|
| **XSS via v-html** — LLM-Output wurde ohne Sanitization gerendert (7 Stellen in Step4Report + Step5Interaction) | HOCH | DOMPurify eingebaut, `renderMarkdown()` nach `frontend/src/utils/markdown.js` extrahiert | b763691 |
| **Cypher Label Injection** — Entity-Types aus NER via f-string in Cypher-Queries (neo4j_storage.py:286, 444) | HOCH | `_sanitize_label()` mit Regex `^[A-Za-z][A-Za-z0-9_]*$`, unsafe Labels werden abgewiesen | b763691 |

#### Code-Quality-Fixes (MIR-17 Benchmark)

| Befund | Fix |
|--------|-----|
| Near-Duplicate-Detection zählte Exact-Dupes doppelt → Quality Score zu niedrig | Exact-Dupe-Hashes aus Near-Dupe-Scan ausgeschlossen |
| `benchmark.end_phase("report")` nur auf Happy-Path → verwaiste Timestamps | In `finally`-Block verschoben |
| `benchmark.save()` in simulation_manager.py ohne try/except → Disk-Fehler bricht Pipeline | try/except konsistent mit anderen Aufrufstellen |
| Config-Generator greift direkt auf `LLMClient._token_counts` zu | `LLMClient.record_usage()` API eingeführt |
| LLM-Logger `propagate=True` flutet Haupt-Log mit Debug-Output | `propagate=False` + WARNING-Console-Handler |

#### Bewusst nicht adressiert (localhost-Scope)

Folgende Befunde wurden identifiziert aber als irrelevant für den Localhost-Betrieb eingestuft:
- Keine Authentifizierung/Autorisierung (CORS `origins: "*"`)
- Keine Rate-Limiting, keine Ownership-Checks
- Unverschlüsselte Neo4j-Verbindung (`bolt://` statt `bolt+ssc://`)
- Hardcoded SECRET_KEY Fallback, Debug-Modus Default True
- Traceback-Exposure in API-Responses

Diese Punkte sind relevant falls Simulab je in einem Mehrbenutzerbetrieb oder über Netzwerk eingesetzt wird.

---

## 4. Benchmark-Ergebnisse

### 4.1 Testaufbau

- **Hardware:** Mac Studio, Apple M2 Ultra, 128 GB RAM (Setup-Tests zusätzlich auf Mac Studio M4 Max, 128 GB RAM)
- **Seed-Text (Haupt-Benchmark):** Pharma Advisory Board Briefing für GlucoShield® (9.589 Zeichen)
- **Seed-Text (Quick-Benchmark):** Fiktiver Greendale Car-Free Sundays Artikel (380 Wörter, `backend/uploads/greendale_carfree_sundays.txt`) — für schnelle Modell-Vergleiche ohne vollständige Simulation
- **Simulationsumfang:** 40 Runden (sofern nicht anders angegeben), Twitter + Reddit
- **Konstanten:** NER-Modell phi4-mini-ner (3.3 GB), Embeddings qwen3-embedding:0.6b-fp16 (1024d)

**Quick-Benchmark-Methodik:** Das Greendale-Seed wurde in der Setup-Phase entwickelt, um neue Modelle schnell zu evaluieren bevor der vollständige Pharma-Benchmark (~5h) läuft. Der Quick-Test prüft Graph-Build (Nodes/Edges, JSON-Fehlerrate, Chunk-Timings) und Persona-Generierung (Hybrid-Search-Qualität), dauert aber nur ~5-20 Min je nach Modell. Der zugehörige Simulations-Prompt liegt in `backend/uploads/greendale_simulation_prompt.txt`.

**Hinweis:** Das Upstream-Repo (666ghj/MiroFish) enthält **keine Beispieldaten** — weder Fixtures, Demo-Events noch herunterladbare Seeds. Die offiziellen Demos (Wuhan University Public Opinion, Dream of the Red Chamber) sind nur als Bilibili-Videos verfügbar. Der Workflow ist komplett Upload-getrieben.

#### Quick-Benchmark-Ergebnisse (Greendale-Seed, 380 Wörter)

| Modell | Nodes | Edges | JSON-Fehler | Chunk-Verlust | Dauer Graph-Build | Hybrid-Search |
|--------|-------|-------|-------------|---------------|-------------------|---------------|
| qwen2.5:14b Q4 | 12 | 5 | 0/8 | 0% | ~30s | 5 facts, 23 nodes |
| gemma4-direct (SYSTEM no-think) | 5 | 1 | 5/8 | 25% | ~9.5 Min | — |
| ministral-3:14b Q8 (768d mismatch) | 22 | 27 | 0/8 | 0% | ~2 Min | 11 facts, **1 node** (BM25-only) |
| **ministral-3:14b Q8 (1024d korrekt)** | **24** | **23** | **0/8** | **0%** | **~90s** | **23 facts, 39 nodes** |

### 4.2 Pipeline-Timing

| Modell | Quant | RAM | MIR-22 | Agents | Prepare | Simulation | Report | **Gesamt** |
|--------|-------|-----|--------|--------|---------|------------|--------|------------|
| Qwen 2.5:14b | Q4 | 8 GB | nein | 59 | 13 Min | 2h 30min | 9 Min | **2h 53min** |
| Ministral-3:14b | Q4 | 8 GB | nein | 74 | 17 Min | 3h 08min | 11 Min | **3h 25min** |
| Qwen 2.5:14b | Q8 | 15 GB | nein | 72 | 22 Min | 3h 52min | 6 Min | **4h 20min** |
| Ministral-3:14b | Q4 | 8 GB | ja | 76 | 65 Min | 3h 20min | — | **4h 25min** |
| Qwen 2.5:32b | Q4 | 17 GB | ja+Fixes | 75 | 39 Min | 4h 22min | 9 Min | **5h 09min** |
| Qwen 2.5:32b | Q8 | 33 GB | nein | 74 | 45 Min | 4h 27min | 17 Min | **5h 29min** |
| Qwen 2.5:32b | Q4 | 17 GB | ja | 79 | 60 Min | 8h 29min | 14 Min | **9h 28min** * |

\* 72 Runden statt 40, ohne Narrative Guidance und ohne Initial Posts

### 4.3 Content-Qualität

| Modell | Quant | MIR-22 | Posts | Dupes | Non-EN | Emojis/P | Hash/P | StdDev Words | **Score** |
|--------|-------|--------|-------|-------|--------|----------|--------|-------------|-----------|
| Qwen 32b | Q8 | nein | 71 | 20 | 0.0% | 0.14 | 0.57 | 7.6 | **70.0** |
| **Qwen 32b** | **Q4** | **ja+Fixes** | **96** | **28** | **1.2%** | **0.35** | **0.66** | **—** | **68.1** |
| Ministral | Q4 | nein | 153 | 70 | 0.0% | 0.05 | 0.70 | 12.7 | **62.5** |
| Qwen 14b | Q4 | nein | 159 | 63 | 0.6% | 0.02 | 0.96 | 14.3 | **57.4** |
| Qwen 14b | Q8 | nein | 168 | 76 | 1.9% | 0.00 | 0.43 | 12.6 | **53.2** |
| Ministral | Q4 | ja | 105 | 42 | 0.0% | 1.51 | 2.36 | 58.9 | **38.1** * |
| Qwen 32b | Q4 | ja (ohne Fixes) | 102 | 42 | 0.0% | 2.04 | 3.96 | 44.1 | **26.0** * |

\* Scores vor Quality-Score-Rekalibrierung — mit angepasster Formel wären diese höher

#### Quality-Score-Rekalibrierung (MIR-17 Nachkalibrierung)

Die ursprünglichen Sweet Spots waren zu eng gefasst und bestraften realistische Social-Media-Posts:

| Metrik | Alt | Neu | Begründung |
|--------|-----|-----|------------|
| Avg Word Length | 15-50 | 30-120 | 120 Wörter ≈ ein Reddit-Post, realistischer Oberwert |
| Emoji/Post | 0.1-0.5 | 0.1-1.0 | 1 Emoji/Post ist im Social-Media-Kontext normal |
| Hashtag/Post | 0.2-1.0 | 0.2-2.0 | 2 Hashtags/Post noch im realistischen Bereich |

Die Penalty-Ramps wurden entsprechend angepasst (lineare Abklingzonen: Word 10→30 und 120→200, Emoji 1.0→3.0, Hashtag 2.0→5.0). Die mit \* markierten Scores in Tabelle 4.3 wären mit der neuen Formel höher — die Werte in der Tabelle sind die zum Messzeitpunkt berechneten und wurden nicht nachträglich umgerechnet.

### 4.4 Report-Qualität

| Modell | Fixes | Narrative | Sections | Wörter |
|--------|-------|-----------|----------|--------|
| Qwen 32b Q4 | ja (72R, ohne Narrative) | NEIN | 5 | **5.160** |
| Ministral Q4 | nein | ja | 4 | 1.946 |
| Qwen 32b Q8 | nein | ja | 5 | 1.906 |
| Qwen 14b Q4 | nein | ja | 5 | 1.838 |
| Qwen 14b Q8 | nein | ja | 4 | 1.610 |
| Qwen 32b Q4 | ja+Fixes | ja (neutral) | 4 | 1.251 |

### 4.5 Persona-Qualität (MIR-22 Vergleich)

| Run | Avg Wörter | Min/Max | 200+ Wörter |
|-----|-----------|---------|-------------|
| Qwen 14b Q4 (ohne MIR-22) | 127 | 87/224 | ~10% |
| Qwen 32b Q8 (ohne MIR-22) | 135 | 90/221 | ~10% |
| Qwen 32b Q4 (MIR-22, ohne Fixes) | 188 | 70/1275 | ~40% |
| Qwen 32b Q4 (mit Fixes) | 236 | 42/325 | 81% |

---

## 5. Verhaltens-Erkenntnisse

### 5.1 Emergenz schlägt Steuerung

**Schlüsselfund:** Die Simulation funktioniert besser ohne vorgegebene Narrative Direction.

- **Mit Narrative:** Das LLM beschreibt vorab wie sich Meinungen entwickeln sollen → Agents folgen dem vorgegebenen Arc → Self-Fulfilling Prophecy → kürzere, generischere Reports (1.200-1.900 Wörter)
- **Ohne Narrative:** Agents interagieren nur basierend auf ihren Personas → emergente Meinungsdynamik → überraschendere, authentischere Ergebnisse → der längste und selbstreflektierteste Report (5.160 Wörter mit Section "Simulation Limits")

**Implikation für den Einsatz:** Simulab liefert die wertvollsten Ergebnisse wenn man die Agents NICHT steuert. Die Simulation ist ein Entdeckungsinstrument, kein Bestätigungsinstrument.

### 5.2 Quantisierung: Q4 ist oft besser als Q8

| Dimension | Q4 | Q8 |
|-----------|-----|-----|
| Fremdsprach-Drift | Gering (0.0-0.6%) | Höher (1.9-8.8%) |
| Speed | 2x schneller | 2x langsamer |
| RAM | Halb so viel | Doppelt |
| Post-Qualität | Vergleichbar | Vergleichbar |

**Erklärung:** Q8 behält mehr der mehrsprachigen Trainingsdaten bei → das Modell "erinnert sich" an chinesische/thailändische Trainingsbeispiele und driftet häufiger in andere Sprachen. Q4 "vergisst" diese effektiver — in diesem Anwendungsfall ein Vorteil.

**Sweet Spot:** Qwen 2.5:32b Q4 — Quality Score 68.1 (nahe am 32b Q8 mit 70.0), halber RAM (17 GB vs. 33 GB), 0% Fremdsprache.

### 5.3 Persona-Länge als Qualitätstreiber

Längere Personas → reichere, differenziertere Posts. Aber das LLM stoppt freiwillig bei ~200-250 Wörtern, selbst wenn das Limit 800 beträgt. Explizite Minimum-Anforderungen und Pflicht-Dimensionen (Example Quotes, Known Objections, Boundaries) erzwingen detailliertere Personas.

### 5.4 Emoji/Hashtag-Dampening ist essentiell

Die Anweisung "write like on social media" führt dazu, dass LLMs ihre Antworten mit Emojis und Hashtags überfrachten (2+ Emojis, 4+ Hashtags pro Post). Explizite Dämpfung ("max 1-2 emojis, not every post; max 2 hashtags") bringt die Werte in einen realistischen Bereich.

### 5.5 Initial Posts bestimmen die Diskussionsrichtung

Die generierten `initial_posts` sind der stärkste Einflussfaktor auf den Simulationsverlauf. Sie setzen die Themen und den Ton — alle Agent-Interaktionen bauen darauf auf. Die Möglichkeit, Initial Posts vor dem Start zu sehen und Discussion Topics zu editieren (MIR-10), gibt dem Nutzer wichtige Steuerungsmöglichkeiten ohne die Emergenz zu untergraben.

### 5.6 Config-Generator: Was OASIS tatsächlich nutzt

Eine detaillierte Code-Analyse (vor MIR-10) ergab, dass der Config-Generator (7 Schritte) zahlreiche Parameter generiert, von denen OASIS nur einen Bruchteil tatsächlich konsumiert:

| Config-Feld | Von OASIS genutzt? | Wie? |
|-------------|-------------------|------|
| `active_hours` | **Ja** | Bestimmt wann ein Agent aktiv wird (Stunden-Check pro Runde) |
| `activity_level` | **Ja** | Wahrscheinlichkeit ob Agent in aktiver Stunde tatsächlich handelt |
| `initial_posts` (Content + Poster) | **Ja** | Werden als `ManualAction(CREATE_POST)` in Runde 0 eingespeist |
| `hot_topics` | Nein | Nur Dokumentation in `simulation_config.json` |
| `narrative_direction` | Nein | Nur Dokumentation — enthält aber vorweggenommene Akzeptanzraten und Kippunkte |
| `sentiment_bias` | Nein | In `AgentActivityConfig` generiert, aber von OASIS nie gelesen |
| `stance` | Nein | Dito — "supportive/opposing/neutral" wird ignoriert |
| `influence_weight` | Nein | Dito |

**Implikation:** Die vom Config-Generator erzeugten Sentiment- und Stance-Werte suggerieren Steuerbarkeit, haben aber keinen Effekt auf die Simulation. Die tatsächliche Meinungsdynamik entsteht ausschließlich aus (1) den Persona-Texten, (2) den Initial Posts, und (3) dem Verhalten des Haupt-LLMs während der OASIS-Simulation. Diese Erkenntnis motivierte MIR-10 (Config-Generator Bias reduzieren).

---

## 6. Architektur

### 6.1 Pipeline-Flow

```
Seed-Text (PDF/MD/TXT)
  ↓
Chunking (500 Zeichen, Wortgrenzen-aware)
  ↓
NER/Relation-Extraction (separates kleines Modell: phi4-mini-ner)
  ↓
Knowledge Graph (Neo4j, Hybrid-Search: 0.7 Vektor + 0.3 BM25)
  ↓
Entity-Filtering (nach Typ: Person, Organization, etc.)
  ↓
Persona-Generation (LLM, 600-1200 Wörter pro Agent, 9 Pflicht-Dimensionen)
  ↓
Config-Generation (LLM: Zeitkonfiguration, Activity-Levels, Discussion Topics)
  ↓
OASIS Dual-Platform Simulation (Twitter + Reddit, parallel)
  ↓
Report-Agent (ReACT-Pattern: Plan → Generate → Reflect)
  ↓
Agent-Chat (IPC-basiert, Echtzeit-Interview mit einzelnen Agents)
```

### 6.2 Drei-Modell-Architektur

Simulab nutzt 3 separate Modelle für verschiedene Aufgaben:

| Modell | Aufgabe | Typische Größe | Konfiguration |
|--------|---------|---------------|---------------|
| **Haupt-LLM** | Persona-Generierung, Config, Simulation, Report | 14b-32b (8-33 GB) | `LLM_MODEL_NAME` |
| **NER-Modell** | Entity/Relation-Extraction aus Seed-Text | 3b-4b (3 GB) | `NER_MODEL_NAME` |
| **Embedding-Modell** | Vektor-Embeddings für Graph-Search | 0.6b (1 GB) | `EMBEDDING_MODEL` |

### 6.3 Zentrale Stellschrauben

| Stellschraube | Wo | Effekt |
|---------------|-----|--------|
| **Persona-Länge** | `oasis_profile_generator.py:662` | Längere Personas → reichere Posts, aber langsamere Inference |
| **Post-Length-Guidance** | `oasis_profile_generator.py:_get_post_length_guidance()` | Steuert Variation der Post-Länge pro Entity-Type |
| **Narrative Mode** | `simulation_config_generator.py` + Step2 UI | Neutral (emergent) vs. Guided (gerichtet) |
| **Discussion Topics** | Step2 UI (editierbar) | Themen die Agents diskutieren |
| **Activity-Config** | `simulation_config_generator.py:AgentActivityConfig` | Peak-Hours, Agents/Stunde, Activity-Multiplier |
| **OUTPUT_LANGUAGE** | `.env` + alle Prompt-Templates | Erzwingt Sprache der generierten Inhalte |
| **Modell-Wahl** | `.env: LLM_MODEL_NAME` | Größtes Impact auf Qualität und Speed |
| **NER-Modell** | `.env: NER_MODEL_NAME` | Separates kleines Modell verhindert RAM-Konkurrenz |
| **Embedding-Dimension** | Auto-detected oder `.env: EMBEDDING_DIMENSION` | Automatische Migration bei Modellwechsel |
| **Simulationsrunden** | Frontend (Step 2) | LLM schlägt vor (72-336), User wählt (typisch 40) |

### 6.4 Deployment-Architektur

```
┌─────────────────────────────────────────────────┐
│  Mac Studio (Host)                               │
│                                                   │
│  ┌─────────────┐    ┌──────────────────────────┐ │
│  │   Ollama     │    │  Docker                   │ │
│  │  Port 11434  │◄───│  ┌─────────────────────┐ │ │
│  │  (nativ,     │    │  │ mirofish-offline     │ │ │
│  │   Metal GPU) │    │  │  Backend :5001       │ │ │
│  └─────────────┘    │  │  Frontend :3000      │ │ │
│                      │  └────────┬────────────┘ │ │
│                      │           │               │ │
│                      │  ┌────────▼────────────┐ │ │
│                      │  │ mirofish-neo4j       │ │ │
│                      │  │  Browser :7474       │ │ │
│                      │  │  Bolt :7687          │ │ │
│                      │  └─────────────────────┘ │ │
│                      └──────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Netzwerk-Konfiguration:**
- Container → Host-Ollama: `http://host.docker.internal:11434` (Docker-interne DNS-Auflösung)
- Container → Neo4j: `bolt://neo4j:7687` (Docker-Netzwerk, Service-Name)
- Host → Frontend: `http://localhost:3000`
- Host → Backend: `http://localhost:5001`

**Persistenz:**
- Neo4j-Daten: Docker Named Volume (`neo4j_data:/data`)
- Reports/Uploads: Bind-Mount (`./backend/uploads:/app/backend/uploads`) — Dateien liegen direkt auf dem Host-Dateisystem
- Simulationsstatus: `state.json` pro Simulation — steuert Restart-Verhalten

**Operational Tips:**
- `docker compose restart` lädt `.env`-Änderungen **nicht** neu → `docker compose down && docker compose up -d` verwenden
- Simulation wird bei Container-Restart automatisch fortgesetzt (basierend auf `state.json`). Zum Verhindern: `status` in `state.json` auf `"failed"` setzen vor dem Restart.
- Container braucht `deploy.resources.limits.memory: 32g` für Dual-World-Simulation mit >50 Agenten

### 6.5 LLM-Concurrency

Die Pipeline feuert an mehreren Stellen parallele LLM-Requests ab:

| Stelle | Mechanismus | Default | Konfiguration |
|--------|-------------|---------|---------------|
| OASIS Simulation (pro Plattform) | asyncio Semaphore | 30 | `LLM_MAX_CONCURRENT` in `.env` |
| Dual-Platform (Twitter+Reddit) | `asyncio.gather()` | 2× parallel | Nicht konfigurierbar |
| Profil-Generierung | `ThreadPoolExecutor` | 5 Worker | `min(parallel_count, LLM_MAX_CONCURRENT)` |

Für Ollama mit `OLLAMA_NUM_PARALLEL=4` ist `LLM_MAX_CONCURRENT=30` sinnvoll (Ollama queued intern). Für Backends die nur einen Request gleichzeitig verarbeiten (z.B. LM Studio MLX): `LLM_MAX_CONCURRENT=1`.

### 6.6 Wie Agent-Verhalten entsteht

Das OASIS-Framework (CAMEL-AI) steuert die Agent-Interaktionen. Simulab kontrolliert ausschließlich den **Input**:

1. **`user_char`** (Twitter CSV) bzw. **`persona`** (Reddit JSON) — wird als System-Prompt an das LLM übergeben
2. **`simulation_config.json`** — definiert wann und wie oft Agents aktiv sind
3. **`initial_posts`** — Seed-Posts die die Diskussion anstoßen

Was Simulab **nicht** kontrolliert:
- Die interne Entscheidungslogik von OASIS (welcher Agent wann welche Aktion wählt)
- Die genaue Prompt-Formatierung die OASIS an das LLM sendet
- Die Reihenfolge der Agent-Aktivierung pro Runde

---

## 7. Modell-Empfehlungen

### 7.1 Empfehlungsmatrix

| Einsatz | Empfohlenes Modell | Dauer (40R) | Qualität | RAM |
|---------|-------------------|-------------|----------|-----|
| **Quick-Test / Prototyping** | Qwen 2.5:14b Q4 | ~3h | Gut | 8 GB |
| **Standard-Simulation** | Qwen 2.5:32b Q4 | ~5h | Sehr gut | 17 GB |
| **Maximale Qualität** | Qwen 2.5:32b Q8 | ~5.5h | Exzellent | 33 GB |
| **Alternative (kein Qwen)** | Ministral-3:14b Q4 | ~3.5h | Gut | 8 GB |
| **Nicht empfohlen** | Qwen 2.5:14b Q8 | ~4.5h | Schlecht | 15 GB |

### 7.2 Sweet Spot

**Qwen 2.5:32b Q4** mit Persona-Optimierungen und Emoji-Dämpfung:
- Quality Score 68.1 (nahe am Maximum 70.0 des 32b Q8)
- Halber RAM-Verbrauch (17 GB vs. 33 GB)
- 0% Fremdsprache (mit Q4)
- Gute Post-Längen-Variation (Min 2, Max 50 Wörter auf Twitter)
- Initial Posts und Discussion Topics für aktive Diskussionen

### 7.3 Evaluierte aber nicht empfohlene Modelle

**Qwen3.5-35B-A3B (MoE, 3B aktive Parameter)**

Auf dem Papier der vielversprechendste Kandidat: MoE-Architektur (nur 3B aktive Parameter bei 35B total), ~130 tok/s auf Apple Silicon via Ollama MLX, ~20 GB RAM bei Q4, multimodal. Wurde im Review-Chat evaluiert (April 2026) und **nicht** empfohlen aus folgenden Gründen:

1. **JSON-Format-Bug bei `think: false`** (ollama/ollama#14645 — zum Evaluierungszeitpunkt offen): Wenn Thinking deaktiviert wird, funktioniert Ollamas JSON-Format-Enforcement nicht. Das Modell ignoriert `format: json`. Showstopper für Simulab — die gesamte Pipeline braucht zuverlässiges JSON.
2. **Thinking nicht per Modelfile deaktivierbar** — nur per-Request via `think: false` in `extra_body`, erfordert Anpassung des LLMClient.
3. **Bisherige Erfahrung mit Thinking-Modellen durchweg negativ**: Gemma 4 (25% Chunk-Verlust), GLM 4.7 Flash (100% Reasoning-Loop), DeepSeek-R1 (Thinking-Loop).

**Empfehlung:** Qwen3.5/3.6-35B-A3B erneut evaluieren sobald ollama/ollama#14645 gefixt ist. Dann direkt Qwen3.6 (neuere Iteration) testen.

**Grundregel:** Thinking-Modelle sind für Simulab ungeeignet bis Ollama zuverlässiges `think: false` + `format: json` in Kombination unterstützt.

**Gemma 4:26b-a4b-it-q8_0 (28 GB)**

Im Setup-Chat (April 2026) ausführlich getestet mit dem Ziel, Thinking per `think: false` über Ollamas OpenAI-kompatiblen Endpoint (`/v1/chat/completions`) zu deaktivieren.

| Test | Ergebnis |
|------|---------|
| `think: false` via `extra_body` auf `/v1` | **Ignoriert** — Modell denkt intern, `/v1`-Response enthält `reasoning`-Feld neben `content` (ollama/ollama#15293) |
| `think: false` via native API (`/api/chat`) | Funktioniert korrekt |
| Ontologie-Generierung (mit `response_format: json_object`) | Erfolgreich (7503 chars, 158s), aber nur bei ausreichend `num_ctx` |
| NER-Extraktion (36 Chunks) | ~30% der Chunks liefern 0 chars nach ~60s — Modell "denkt" intern und Content ist leer |
| Graph-Build Ergebnis | Nur 15 Nodes / 4 Edges (vs. 55 Nodes / 86 Edges bei Ministral-3 ohne Thinking) |

**Debugging-Verlauf:** Anfangs wurde `response_format: json_object` als Ursache vermutet und für Ollama deaktiviert. Direkte API-Tests (`curl` + OpenAI SDK im Container) zeigten jedoch, dass `response_format` funktioniert — das eigentliche Problem war ein zu kleines Context-Fenster (`OLLAMA_NUM_CTX=8192` statt 32768). Auch nach Korrektur des Context-Fensters blieben ~30% der NER-Chunks leer: Bei diesen Chunks verbrauchte das Modell alle verfügbaren Tokens für internes Reasoning.

**Zweiter Testlauf (Setup-Chat 2, Modelfile-Ansatz):** In einer Folgesession wurde ein alternativer Ansatz eines Kollegen getestet — Thinking-Unterdrückung per Ollama-Modelfile mit `SYSTEM "Do not use thinking mode. Respond directly without any internal reasoning."` statt `think: false` per Request. Ergebnis:

| Test | Ergebnis |
|------|---------|
| `ollama run gemma4-direct "List 3 fruits."` (CLI) | Modell denkt noch sichtbar ("Thinking... ...done thinking."), aber finale Antwort sauber |
| `/v1/chat/completions` (API) | **Antwort clean** — Ollama filtert Thinking-Block auf API-Ebene heraus |
| NER-Extraktion (8 Chunks, Greendale-Seed) | **5 JSON-Fehler**, 2 Chunks komplett verloren (25% Verlust, 177s pro verlorenem Chunk) |
| Graph-Build Ergebnis | Nur **5 Nodes / 1 Edge** (vs. 24/23 bei Ministral, 12/5 bei Qwen 2.5:14b) |
| Gesamtdauer | **~9.5 Min** (vs. ~90s bei Ministral, ~30s bei Qwen 2.5:14b) |

**Wichtige Erkenntnis:** Ollama filtert den Thinking-Block automatisch in der `/v1`-API-Response heraus — das SYSTEM-Prompt-basierte Modelfile unterdrückt Thinking auf Output-Ebene effektiv. Das CLI (`ollama run`) zeigt den Thinking-Prozess noch transparent an, die API liefert aber saubere Responses. Das eigentliche Problem ist **nicht** Thinking-Leakage, sondern grundsätzlich schlechte JSON-Compliance des Modells.

**Fazit:** Gemma 4 ist für Simulab aus zwei unabhängigen Gründen ungeeignet: (1) `think: false` funktioniert nicht über `/v1`, und (2) selbst bei erfolgreicher Thinking-Unterdrückung (per SYSTEM-Prompt) ist die JSON-Compliance deutlich schlechter als bei Non-Thinking-Modellen.

### 7.4 LM Studio als LLM-Backend — Evaluiert und nicht empfohlen

LM Studio wurde als Alternative zu Ollama evaluiert, insbesondere wegen der Möglichkeit MLX-Modelle direkt zu laden. Ergebnis: **nicht empfohlen** für Simulab.

**Evaluierte Modelle in LM Studio:**

| Modell | Ergebnis | Problem |
|--------|----------|---------|
| Gemma 4 26B A4B (MLX 8-bit) | Konnte nicht geladen werden | `mlx_vlm` in LM Studio hat keinen Gemma-4-Support (lmstudio-ai/mlx-engine#301) |
| GLM 4.7 Flash 30B-A3B (MLX 8-bit) | Katastrophal | Thinking-Loop: 4095/4096 Tokens für `reasoning_content`, 0 Tokens für `content`. Antworten leer oder minimal. |
| Ministral-3 14B Instruct (MLX) | Funktioniert | 0 Reasoning Tokens, saubere JSON-Ausgabe, gute Geschwindigkeit |

**Strukturelle Probleme mit LM Studio für Simulab:**

1. **`response_format: json_object` nicht unterstützt** — LM Studio akzeptiert nur `json_schema` oder `text`. Erfordert Code-Anpassungen an allen Stellen die JSON anfordern (LLMClient, SimulationConfigGenerator, OasisProfileGenerator).
2. **Nur 1 Request gleichzeitig** — MLX-Modelle in LM Studio sind auf `Max Concurrent Predictions: 1` fixiert. Simulab feuert aber bis zu 60 parallele Requests ab (Semaphore 30 × 2 Plattformen).
3. **Ollama 0.19+ nutzt MLX nativ** — Seit April 2026 hat Ollama ein eigenes MLX-Backend für Apple Silicon. Der Hauptvorteil von LM Studio (MLX-Support) entfällt damit.
4. **Kein Modelfile-Konzept** — Ollama-Modelfiles erlauben persistente `num_ctx`-Konfiguration. In LM Studio muss Context Length manuell bei jedem Laden eingestellt werden.

**Alternative: `mlx-lm` als Standalone-Server** wurde diskutiert (`mlx_lm.server --model ... --port 1234`), aber ebenfalls nicht weiterverfolgt da Ollama MLX nativ unterstützt.

**Fazit:** Ollama ist das empfohlene Backend. LM Studio bietet keinen Mehrwert und hat mehrere Inkompatibilitäten mit Simulabs Pipeline.

### 7.6 Ollama-Modelfile-Konfiguration

**Warum Modelfiles essentiell sind:** Ohne Modelfile alloziert Ollama den **vollen Default-Context** des Modells als KV-Cache beim ersten Laden. Bei Ministral-3 14B sind das 262k Tokens → 59 GB RAM (davon ~44 GB nur KV-Cache). Dies wurde im Setup-Chat diagnostiziert als `ollama ps` 59 GB anzeigte, obwohl das Modell nur 15 GB Gewichte hat. Die per `extra_body` übergebene `num_ctx`-Konfiguration wird beim Request zwar akzeptiert, ändert aber nicht den bereits allozierten KV-Cache. Ein Modelfile mit `PARAMETER num_ctx 32768` löst das Problem: Ollama lädt das Modell direkt mit 32k Context → 21 GB statt 59 GB.

**Temperature:** Modelfile-Temperature wird nur als Fallback verwendet — Simulab setzt Temperature per Request (NER: 0.1, JSON: 0.3, Personas: 0.7, Default: 0.8). Temperature 0.15 im Modelfile war ein Fehler aus frühen NER-Tests und wurde auf 0.8 korrigiert, damit die OASIS-Simulation diverse Agent-Outputs erzeugt.

**Verfügbare Modelfiles:**

| Modelfile | Basis | num_ctx | RAM (geschätzt) |
|-----------|-------|---------|-----------------|
| `ministral-3:14b-q4-mirofish` | Q4 (9 GB) | 32768 | ~13 GB |
| `ministral-3:14b-mirofish` | Q8 (15 GB) | 49152 | ~24 GB |

**num_ctx 49152 (1.5×):** Im Setup-Chat 2 wurde num_ctx von 32768 auf 49152 erhöht (Faktor 1.5). Ministral lief stabil mit 49152 Context bei 19 Agenten — kein OOM, keine leeren Antworten. KV-Cache-Overhead steigt um ~50%, aber bei 128 GB RAM kein Problem. Der höhere Context bietet Reserve für längere Seed-Texte und komplexere Persona-Prompts.

**Parallelisierung:** `OLLAMA_NUM_PARALLEL` (Default: 1) und `OLLAMA_MAX_LOADED_MODELS` (Default: 1) können die Pipeline deutlich beschleunigen. Bei 128 GB RAM und Q4-Modell ist `NUM_PARALLEL=4` + `MAX_LOADED_MODELS=3` (Haupt-LLM + phi4-mini NER + qwen3-embedding) realistisch. Geschätzte Persona-Generierung: 30-60 Min → 8-15 Min.

```bash
# macOS (persistent bis Reboot):
launchctl setenv OLLAMA_NUM_PARALLEL 4
launchctl setenv OLLAMA_MAX_LOADED_MODELS 3
# Dann Ollama neustarten
```

---

## 8. Einsatzszenarien

### 8.1 Pharma Launch-Testing

**Situation:** Ein Pharma-Unternehmen plant den Launch von GlucoShield®, einem neuen GLP-1-Rezeptoragonisten. Vor dem echten Advisory Board soll getestet werden, wie Ärzte, Patienten und Versicherer reagieren.

**Simulab-Einsatz:**
- Seed-Text: Advisory Board Briefing (10.000 Zeichen)
- Ergebnis: 75 Stakeholder-Personas, 40 Runden Diskussion, Report mit Empfehlungen
- Dauer: 5 Stunden
- Output: "Recommended Message Adjustment for Phase 2 Testing"

**Vergleich:** Ein echtes Advisory Board kostet 50.000-100.000 EUR und 3 Monate Vorlauf. Eine Simulab-Simulation kostet 5 Stunden Rechenzeit und kann beliebig oft iteriert werden.

### 8.2 Krisenmanagement

**Situation:** Ein internes Dokument könnte an die Presse gelangen. Wie reagieren verschiedene Stakeholder?

**Simulab-Einsatz:**
- Seed-Text: Das potentiell geleakte Dokument
- Neutral Mode: Keine vorgegebene Richtung, rein emergente Reaktionen
- Ergebnis: Welche Gegennarrative entstehen? Wo kippt die Stimmung? Welche Stakeholder verbünden sich?

### 8.3 Workshop-Begleitung

**Situation:** Ein Strategie-Workshop soll Stakeholder-Reaktionen auf eine neue Initiative diskutieren.

**Simulab-Einsatz (3 Phasen):**
1. **Vor dem Workshop:** Simulation mit dem Briefing-Dokument laufen lassen
2. **Im Workshop:** Simulations-Report als Diskussionsgrundlage präsentieren. "Die KI-Stakeholder haben X gesagt — stimmt ihr zu?"
3. **Nach dem Workshop:** Parameter anpassen (z.B. Message-Varianten), neue Simulation, Vergleich

### 8.4 Politische Kommunikation

**Situation:** Eine Regierungsbehörde plant eine Policy-Änderung und will wissen, wie verschiedene Bevölkerungsgruppen reagieren.

**Simulab-Einsatz:**
- Seed-Text: Entwurf der Policy-Ankündigung
- 60-80 automatisch generierte Stakeholder (Betroffene, Befürworter, Medien, Opposition)
- Ergebnis: Welche Argumente dominieren? Wo entsteht Widerstand? Welche Messaging-Strategie funktioniert?

### 8.5 Markenpositionierung

**Situation:** Ein Unternehmen repositioniert seine Marke und will wissen, wie die Zielgruppe reagiert.

**Simulab-Einsatz:**
- Seed-Text: Positionierungs-Dokument mit Kernbotschaften
- Iterativer Prozess: 1. Run → Schwächen identifizieren → Botschaft anpassen → 2. Run → vergleichen

### 8.6 Competitive Intelligence

**Situation:** Wie reagieren Wettbewerber und deren Stakeholder auf den eigenen Produkt-Launch?

**Simulab-Einsatz:**
- Seed-Text: Eigene Pressemitteilung + öffentlich verfügbare Wettbewerber-Informationen
- Ergebnis: Simulation generiert automatisch Wettbewerber-Personas und deren wahrscheinliche Reaktionen

### 8.7 Interne Kommunikation

**Situation:** Ein Unternehmen plant eine Restrukturierung. Wie reagieren verschiedene Abteilungen?

**Simulab-Einsatz:**
- Seed-Text: Entwurf der internen Mitteilung
- Stakeholder-Personas: Führungskräfte, Mitarbeiter verschiedener Abteilungen, Betriebsrat
- Ergebnis: Welche Bedenken entstehen? Wo ist zusätzliche Kommunikation nötig?

### 8.8 Regulatory Affairs

**Situation:** Wie reagieren Stakeholder auf eine Zulassungsentscheidung (positiv oder negativ)?

**Simulab-Einsatz:**
- Seed-Text: Zulassungsbescheid + Zusammenfassung der klinischen Daten
- Simulation zeigt: Medien-Reaktionen, Patienten-Communities, Wettbewerber, Investoren

---

## 9. Simulab als Produkt: Workshop- & Verkaufsformate

### 9.1 Standalone-Simulation

**Deliverable:** Simulation + Report als eigenständige Dienstleistung.

**Typischer Ablauf:**
1. Kunde liefert Briefing-Dokument (PDF/MD/TXT)
2. Erste Simulation (5 Stunden)
3. Report-Präsentation + Diskussion der Ergebnisse
4. Optional: Anpassung der Parameter, zweiter Run
5. Deliverable: Simulationsreport + Persona-Dokumentation + Empfehlungen

**Preispositionierung:** Ein Advisory Board kostet 50.000-100.000 EUR. Eine Simulab-Analyse liefert in 1-2 Tagen vergleichbare Stakeholder-Insights — als Vorbereitung, Ergänzung oder kosteneffiziente Alternative.

### 9.2 Workshop-Integration

**Simulab als Baustein in bestehenden Strategie-Workshops:**

| Phase | Aktivität | Simulab-Beitrag |
|-------|-----------|----------------|
| **Vorbereitung** | Simulation vor dem Workshop | Report als Diskussionsgrundlage |
| **Workshop Tag 1** | Ergebnisse präsentieren | "Die simulierten Stakeholder sagen X — stimmt ihr zu?" |
| **Workshop Tag 1** | Botschaft anpassen | Teilnehmer iterieren die Kernbotschaften |
| **Zwischen den Tagen** | Zweite Simulation | Neue Botschaft durch Simulation laufen lassen |
| **Workshop Tag 2** | Vergleich präsentieren | "Vorher vs. Nachher — diese Anpassungen haben Y bewirkt" |

### 9.3 Partner-Modell

**Simulab als White-Label-Tool für Agenturen und Beratungen:**

- Partner erhält eigene Instanz (Docker-Setup, eigene Hardware oder gehosteter Mac)
- Eigenes Branding möglich (UI ist konfigurierbar)
- Schulung: 1 Tag für technisches Setup, 1 Tag für Durchführung und Interpretation
- Lizenz: Pro Instanz oder pro Simulationsrun

### 9.4 Limitationen (ehrlich kommuniziert)

1. **Keine Echtzeit-Vorhersage:** Die Simulation bildet plausibles Verhalten ab, keine garantierten Vorhersagen. Sie ersetzt kein echtes Advisory Board — sie ergänzt es.
2. **Modell-abhängige Qualität:** Die Ergebnisse sind nur so gut wie das eingesetzte LLM. Kleinere Modelle produzieren generischere Posts.
3. **Duplikate-Problem:** Aktuell 20-40% Duplikate bei den Posts — die Agents wiederholen sich, besonders bei langen Simulationen.
4. **Kein echtes Sentiment-Learning:** Die Agents lernen nicht wirklich aus Interaktionen. Jeder Post wird unabhängig generiert.
5. **Hardware-Anforderung:** Für gute Ergebnisse: Apple Silicon mit mindestens 32 GB RAM (besser 64-128 GB).
6. **Zeitaufwand:** Eine vollständige Simulation mit Report dauert 3-5 Stunden.
7. **Thinking-Modelle nicht einsetzbar:** Qwen3.5, Gemma 4, GLM 4.7, DeepSeek-R1 — alle haben Probleme mit JSON-Compliance wenn Thinking deaktiviert wird. Beschränkung auf Non-Thinking-Modelle (Qwen 2.5, Ministral-3).
8. **Entity-Type-Coverage unvollständig:** Die Post-Length-Guidance deckt nur ~15 Entity-Types explizit ab. Unbekannte Types (z.B. LLM-erfundene wie "Politician", "Researcher") erhalten nur generische Guidance. Ein Default-Fallback ist vorhanden, aber spezifischere Guidance für häufige Types wäre besser.
9. **Nur Localhost:** Keine Authentifizierung, kein HTTPS, keine Rate-Limiting. Für Mehrbenutzerbetrieb oder Netzwerk-Einsatz müssten Security-Maßnahmen nachgerüstet werden (siehe Abschnitt 3.3).

---

## 10. Contributor Guide

### 10.1 Tech-Stack

| Komponente | Technologie | Zweck |
|-----------|-------------|-------|
| Backend | Python/Flask, AGPL-3.0 | API, Pipeline-Orchestrierung |
| Frontend | Vue 3 + vue-i18n | UI, Simulation-Steuerung |
| LLM | Ollama (lokal) | Persona-/Config-/Post-Generierung |
| NER | Ollama (separates Modell) | Entity/Relation-Extraction |
| Embeddings | Ollama (qwen3-embedding) | Vektor-Embeddings für Graph-Search |
| Graph-DB | Neo4j CE 5.18 | Knowledge Graph, Hybrid-Search |
| Simulation | OASIS/CAMEL-AI | Multi-Agent Social-Media-Simulation |
| Deployment | Docker Compose | Container-Orchestrierung |

### 10.2 Projekt von Grund auf aufsetzen

```bash
# 1. Repository klonen
git clone https://github.com/StefanWeimarPRODOC/MiroFish-Offline.git
cd MiroFish-Offline

# 2. .env erstellen
cp .env.example .env
# Anpassen: LLM_MODEL_NAME, EMBEDDING_MODEL, etc.

# 3. Ollama-Modelle laden
ollama pull ministral-3:14b-instruct-2512-q8_0  # oder anderes Modell
ollama pull qwen3-embedding:0.6b-fp16

# 4. Modelfile für optimalen num_ctx erstellen
cat > Modelfile <<EOF
FROM ministral-3:14b-instruct-2512-q8_0
PARAMETER num_ctx 32768
EOF
ollama create ministral-3:14b-mirofish -f Modelfile

# 5. Docker-Container starten
docker compose up -d

# 6. Zugriff
# Frontend: http://localhost:3000
# Backend:  http://localhost:5001
# Neo4j:    http://localhost:7474
```

**Wichtig:** Ollama muss nativ auf dem Host laufen (nicht im Docker), damit Metal/GPU genutzt wird. Die Docker-Container erreichen Ollama über `host.docker.internal:11434`.

**Bei Wechsel des Embedding-Modells:** Die Neo4j-Vektorindizes müssen zur Dimension des Embedding-Modells passen. `qwen3-embedding` erzeugt 1024d-Vektoren, `nomic-embed-text` erzeugt 768d. Bei Modellwechsel: `docker compose down -v` (löscht Neo4j-Volume) oder die automatische Migration via MIR-8 nutzen.

### 10.3 Ticket-System

- **Tool:** Linear (Team: MiroFish, Key: `MIR`)
- **Commits:** `Part of MIR-XX` (Work in Progress) oder `Fixes MIR-XX` (abgeschlossen)
- **GitHub-Webhook:** Automatische Verknüpfung von Commits und Linear-Issues
- Doku: `docs/linear-workflow.md`

### 10.4 Neuen Benchmark-Run durchführen

1. Modell in `.env` setzen (`LLM_MODEL_NAME`, ggf. `NER_MODEL_NAME`)
2. Seed-Text hochladen, Simulation Prompt eingeben
3. Pipeline komplett durchlaufen lassen (Graph Build → Env Setup → Simulation → Report)
4. Ergebnisse landen automatisch in:
   - `backend/uploads/simulations/sim_{id}/timing.json` — Pipeline-Timing
   - `backend/uploads/simulations/sim_{id}/content_evaluation.json` — Content-Qualität
   - `backend/uploads/simulations/sim_{id}/personas/` — Exportierte Personas

### 10.5 Security-relevante Code-Patterns

| Pattern | Datei | Regel |
|---------|-------|-------|
| **Cypher Label Sanitization** | `neo4j_storage.py` | Entity-Type-Labels werden via `_sanitize_label()` gegen `^[A-Za-z][A-Za-z0-9_]*$` validiert bevor sie in f-string Cypher-Queries interpoliert werden. Neue dynamische Labels müssen durch diesen Check. |
| **HTML Sanitization** | `frontend/src/utils/markdown.js` | Alle LLM-generierten Inhalte die via `v-html` oder `innerHTML` gerendert werden müssen durch `renderMarkdown()` (enthält DOMPurify) oder `sanitizeHtml()`. Niemals Raw-LLM-Output direkt in `v-html`. |
| **Programmatische Keys** | `docs/i18n-audit.md` Abschnitt 5 | Status-Enums, Action-Types, Stage-Keys und Agent-Log-Actions dürfen NIE übersetzt werden. Sie werden per `===` verglichen. Nur Display-Labels übersetzen. |
| **LLM Token Tracking** | `llm_client.py` | Externe Caller (z.B. Config-Generator der eigenen OpenAI-Client nutzt) verwenden `LLMClient.record_usage(response.usage)` statt direktem Zugriff auf `_token_counts`. |
| **Embedding-Dimension** | `neo4j_storage.py` | Nie Dimensionen hardcoden. `EmbeddingService.dimensions` auto-detected oder liest `EMBEDDING_DIMENSION` aus Config. Bei Modellwechsel migriert `_ensure_schema()` automatisch. |

### 10.6 Neues Modell testen

1. Modell in Ollama laden: `ollama pull model-name:tag`
2. `.env` anpassen: `LLM_MODEL_NAME=model-name:tag`
3. Container neu starten: `docker compose restart backend`
4. Simulation laufen lassen
5. `timing.json` und `content_evaluation.json` mit bestehenden Runs vergleichen
6. Bei Embedding-Modellwechsel: Auto-Migration erkennt Dimensionsänderung automatisch

---

## Anhang: Alle Simulation-Runs

| Sim-ID | Modell | Quant | MIR-22 | Fixes | Runden | Agents | Score |
|--------|--------|-------|--------|-------|--------|--------|-------|
| sim_71e391c88bed | Qwen 2.5:14b | Q4 | nein | — | 40 | 59 | 57.4 |
| sim_bc8d536c4357 | Qwen 2.5:32b | Q8 | nein | — | 40 | 74 | 70.0 |
| sim_e30b1d0c8a3e | Qwen 2.5:14b | Q8 | nein | — | 40 | 72 | 53.2 |
| sim_a8b06ac2fd76 | Ministral-3:14b | Q4 | nein | — | 40 | 74 | 62.5 |
| sim_ba82ad5d1856 | Ministral-3:14b | Q4 | ja | — | 40 | 76 | 38.1 |
| sim_fed61e1ac6ed | Qwen 2.5:32b | Q4 | ja | ohne | 72 | 79 | 26.0 |
| sim_a6ce7cc9e0ba | Qwen 2.5:32b | Q4 | ja | mit | 40 | 75 | 68.1 |

---

## Changelog

- **2026-04-30** — Ergänzungen aus Review-Chat (Session 2026-04-22 bis 2026-04-30):
  - MIR-21 und MIR-13 von "offen" nach "erledigt" verschoben (Token-Counting + LLM Call Logging implementiert)
  - Neuer Abschnitt 3.3: Security & Code-Quality Review (XSS-Fix, Cypher Injection Guard, 5 Code-Quality-Fixes)
  - Abschnitt 4.3: Quality-Score-Rekalibrierung dokumentiert (Sweet Spots, Penalty-Ramps)
  - Neuer Abschnitt 7.3: Qwen3.5-35B-A3B Evaluation (Thinking-Modell-Problematik, ollama#14645)
  - Neuer Abschnitt 7.4: Ollama-Modelfile-Konfiguration (Temperature-Fix, Parallelisierung)
  - Abschnitt 9.4: 3 neue Limitationen (Thinking-Modelle, Entity-Type-Coverage, Localhost-Only)
  - Neuer Abschnitt 10.4: Security-relevante Code-Patterns für Contributors
- **2026-04-30** — Ergänzungen aus Pre-Linear Chat 1 (Session 2026-04-09 bis 2026-04-13, Debugging & Modell-Evaluation):
  - Abschnitt 1.1: Fork-Hierarchie korrigiert (nikmcfly als Basis-Fork, nicht direkt 666ghj)
  - Abschnitt 3.1: 5 neue Pre-Ticket-Bugs (leere LLM-Antworten/OLLAMA_NUM_CTX, Ollama 262k Context/59 GB RAM, Neo4j Dimensions-Mismatch, Docker OOM)
  - Abschnitt 3.2: 3 neue Pre-Ticket-Einträge (3 LLM-Call-Stellen, fehlendes Debug-Logging — Entdeckungskontext für MIR-13/MIR-14)
  - Neuer Abschnitt 5.6: Config-Generator-Felder-Analyse (was OASIS tatsächlich nutzt vs. ignoriert — Vorarbeit für MIR-10)
  - Abschnitt 7.3: Gemma 4 Evaluation ergänzt (think:false auf /v1 nicht zuverlässig, Debugging-Verlauf, ollama#15293)
  - Abschnitt 7.5 → 7.6: Kontext zur Modelfile-Notwendigkeit ergänzt (KV-Cache-Diagnose via `ollama ps`)
- **2026-04-30** — Ergänzungen aus Setup-Chat (Session 2026-04-09 bis 2026-04-13):
  - Neuer Abschnitt 1.1: Upstream-Herkunft (chinesischer Markt → deutsche Anpassungen)
  - Neuer Abschnitt 6.4: Deployment-Architektur (Docker ↔ Ollama Netzwerk, Persistenz, Operational Tips)
  - Neuer Abschnitt 6.5: LLM-Concurrency (Semaphore, ThreadPool, `LLM_MAX_CONCURRENT`)
  - Neuer Abschnitt 7.4: LM Studio Evaluation (3 Modelle getestet, strukturelle Probleme, nicht empfohlen)
  - Neuer Abschnitt 10.2: Projekt von Grund auf aufsetzen (Step-by-Step Setup-Anleitung)
  - Hardware-Hinweis in 4.1 ergänzt (M4 Max zusätzlich zu M2 Ultra)
  - Abschnittsnummern in Sektion 10 angepasst (10.2→10.3, 10.3→10.4, etc.)
- **2026-04-30** — Ergänzungen aus Setup-Chat 2 (Session 2026-04-19 bis 2026-04-20, Neuer Fork + Modell-Tests):
  - Abschnitt 3.1: Report-Agent Chat Rendering Bug (Step5Interaction.vue Response-Objekt-Unwrapping, pre-ticket)
  - Abschnitt 3.1: Neo4j Dimensions-Mismatch um quantifizierten Impact ergänzt (1 vs 39 related Nodes)
  - Abschnitt 4.1: Quick-Benchmark-Methodik (Greendale-Seed) und Ergebnistabelle für 4 Modell-Konfigurationen
  - Abschnitt 4.1: Befund dokumentiert dass Upstream keine Demo-Daten enthält
  - Abschnitt 7.3 (Gemma 4): Zweiter Testlauf mit SYSTEM-Prompt-Modelfile-Ansatz dokumentiert — Erkenntnis dass Ollama Thinking auf API-Ebene filtert, Problem ist JSON-Compliance nicht Thinking-Leakage
  - Abschnitt 7.6: num_ctx 49152 (1.5×) Erfahrungswerte ergänzt
