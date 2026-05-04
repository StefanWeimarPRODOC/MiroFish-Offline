# Session-Handoff: MiroFish-Offline (2026-04-24)

## Was wurde in dieser Session erreicht

### MIR-17: Pipeline Benchmarking (implementiert + committed)
- `benchmark_collector.py` — Timing-Collection + Content-Quality-Evaluation
- Automatische `timing.json` + `content_evaluation.json` pro Simulation-Run
- 28 Unit Tests, alle grün
- Commit: `304d138`

### MIR-22: Post-Length-Variation (implementiert in anderem Chat)
- Persona-Limit 500→800 Wörter mit Communication Style + Social Media Behavior
- Entity-type-basierte Post-Length-Guidance in `_get_post_length_guidance()`
- Commit: `deec078`

### Report-Generation Fix
- Escaped JSON braces in PLAN_SYSTEM_PROMPT (MIR-18 Regression)
- LLM-Client: Key-Bereinigung für Ollama-Quirks
- Commit: `304d138`

### Benchmark-Runs durchgeführt (6 Runs)

| Run | Modell | MIR-22 | Runden | Gesamt | Score | Entities |
|-----|--------|--------|--------|--------|-------|----------|
| 1 | Qwen 14b Q4 (8GB) | nein | 40 | 2h 43min | 57.4 | 59 |
| 2 | Qwen 32b Q8 (33GB) | nein | 40 | 5h 29min | 70.0 | 74 |
| 3 | Qwen 14b Q8 (15GB) | nein | 40 | 4h 20min | 53.2 | 72 |
| 4 | Ministral Q4 (8GB) | nein | 40 | 3h 25min | 62.5 | 74 |
| 5 | Ministral Q4 (8GB) | ja | 40 | 4h 25min | 38.1 | 76 |
| 6 | Qwen 32b Q4 (17GB) | ja | 72 | 9h 28min | 26.0 | 79 |

### Neue Linear-Tickets angelegt
- **MIR-19**: Model Selection Guide & Complexity Matrix
- **MIR-20**: Agent-Chat IPC blockiert nach Pause (→ Low, war Timing-Problem)
- **MIR-21**: Token-Counting über gesamte Pipeline
- **MIR-22**: Post-Length-Variation & Persona-Optimierung (implementiert)

### Weitere Artefakte
- `docs/i18n-audit.md` — ~300 Strings für MIR-18 Phase 2 (aktualisiert in anderem Chat)
- MIR-10 aktualisiert: Narrative Guidance neutralisieren + Frontend-Toggle
- MIR-18 aktualisiert: Q8-Quantisierung verstärkt Sprach-Drift, Benchmark-Daten ergänzt

## Nächste Aufgabe: 3 Quick-Wins (je <10 Min)

### Fix 1: Quality-Score Sweet Spots anpassen

**Datei**: `backend/app/services/benchmark_collector.py`, Funktion `_calc_quality_score()`

Die aktuellen Sweet Spots stammen von vor MIR-22. Mit den längeren Posts sind sie zu eng:

| Metrik | Aktuell | Neu |
|--------|---------|-----|
| Avg word length | 15-50 | **30-120** |
| Emoji/post | 0.1-0.5 | **0.1-1.0** |
| Hashtag/post | 0.2-1.0 | **0.2-2.0** |

Penalty-Kurven anpassen:
- Words: 0 pts unter 10, linear 10→30, voll 30-120, linear 120→200, 0 pts über 200
- Emoji: voll 0.1-1.0, linear Penalty 1.0→3.0
- Hashtag: voll 0.2-2.0, linear Penalty 2.0→5.0

**Tests anpassen**: `backend/tests/test_benchmark_collector.py` — `test_perfect_score` und `test_short_posts_penalty` auf neue Werte

### Fix 2: MIR-22 Emoji/Hashtag-Dämpfung

**Datei**: `backend/app/services/oasis_profile_generator.py`, Methode `_get_post_length_guidance()`

An JEDE der 5 Guidance-Varianten (expert, person, journalist, mediaoutlet, organization) diesen Satz anhängen:
```
Use emojis sparingly (0-2 per post, not in every post). Use max 2 hashtags per post.
```

### Fix 3: MIR-10 Narrative Neutralisierung

**Datei**: `backend/app/services/simulation_config_generator.py`

3 Zeilen ändern:

**Zeile ~697** (im Prompt):
```python
# ALT:
- Describe opinion development direction
# NEU:
- List the key discussion topics and open questions for agents to explore (do NOT prescribe how opinions should develop — let dynamics emerge from agent interactions)
```

**Zeile ~706** (im JSON-Template):
```python
# ALT:
"narrative_direction": "<description of opinion development direction>",
# NEU:
"discussion_topics": "<key topics and open questions to explore>",
```

**Zeile ~733** (im Parser):
```python
# ALT:
narrative_direction=result.get("narrative_direction", "")
# NEU:
narrative_direction=result.get("discussion_topics", result.get("narrative_direction", ""))
```

(Der Feldname in EventConfig bleibt `narrative_direction` für Abwärtskompatibilität — nur der Prompt und das JSON-Template ändern sich.)

## Verification

```bash
# Tests
cd backend && uv run pytest tests/test_benchmark_collector.py -v

# Container bauen
docker compose up -d --build mirofish

# Simulation starten mit gleichen Testdaten
# Prüfen:
# - content_evaluation.json → Quality Score 50-80 (statt 26-38)
# - Posts: Emojis <1.0/Post, Hashtags <2.0/Post
# - simulation_config.json → "discussion_topics" statt "narrative_direction"
```

## Aktueller Stand

### .env
```
LLM_MODEL_NAME=qwen2.5:32b
NER_MODEL_NAME=phi4-mini-ner
EMBEDDING_MODEL=qwen3-embedding:0.6b-fp16
OUTPUT_LANGUAGE=English
```

### Git
- Branch: main
- Letzter Commit: `deec078` (MIR-22)
- Alles gepusht

### Ollama
- OLLAMA_NUM_PARALLEL=4, OLLAMA_MAX_LOADED_MODELS=3 (via launchctl)
- Modelle: qwen2.5:32b (Q4), qwen2.5:14b (Q4), qwen2.5:32b-instruct-q8_0, ministral-3:14b-q4-mirofish, phi4-mini-ner, qwen3-embedding

### Simulation-Daten (alle unter backend/uploads/simulations/)
- sim_71e391c88bed — Qwen 14b Q4 (40R)
- sim_bc8d536c4357 — Qwen 32b Q8 (40R)
- sim_e30b1d0c8a3e — Qwen 14b Q8 (40R)
- sim_a8b06ac2fd76 — Ministral Q4 ohne MIR-22 (40R)
- sim_ba82ad5d1856 — Ministral Q4 mit MIR-22 (40R)
- sim_fed61e1ac6ed — Qwen 32b Q4 mit MIR-22 (72R, ohne Narrative Guidance)
