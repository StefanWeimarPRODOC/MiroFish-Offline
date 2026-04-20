# MiroFish-Offline

## Projekt

Lokaler Fork von [MiroFish](https://github.com/666ghj/MiroFish) — Multi-Agent Social-Media-Simulation (Schwarmintelligenz für Meinungsdynamik, Sentiment, soziale Dynamiken). Läuft vollständig lokal auf Apple Silicon, keine Cloud-APIs.

## Stack

- **Backend:** Python/Flask, AGPL-3.0
- **Frontend:** Node.js/React
- **LLM:** Ollama (aktuell ministral-3, konfigurierbar via `.env`)
- **Embeddings:** Ollama (aktuell qwen3-embedding, 1024d)
- **Graph-DB:** Neo4j CE 5.18 (Hybrid-Search: 0.7 Vektor + 0.3 BM25)
- **Deployment:** Docker Compose, Ollama läuft auf Host (nicht im Container)

## Pipeline

```
Seed-Text → Chunking → NER/Relation-Extraction → Knowledge-Graph
→ Agent-Personas (1 pro Person/Org-Entity) → OASIS-Simulation (Twitter/Reddit)
→ Report (ReportAgent mit Agent-Interviews + Graph-Search)
```

Agent-Anzahl wird nicht direkt gesetzt — sie ergibt sich aus der Anzahl benannter Entities im Seed-Text.

## Architektur-Kernkonzepte

- `GraphStorage` ist ein abstraktes Interface — Neo4j-Implementation via `Neo4jStorage`
- Dependency Injection über Flask `app.extensions['neo4j_storage']` — keine globalen Singletons
- Synchrone NER/RE-Extraktion via lokalem LLM (ersetzt Zep Cloud)
- Upstream-Herkunft: chinesischer Markt → dieses Fork ist englisches UI + lokaler Stack

## Ticket-System: Linear

Issue-Tracking läuft über **Linear** (Team: MiroFish, Key: `MIR`, Projekt: MiroFish-Offline Fork).
GitHub-Webhook-Integration ist aktiv — Commits mit `Part of MIR-XX` oder `Fixes MIR-XX` werden automatisch verknüpft.

- Vor Implementierung: Linear-Issue referenzieren
- Commits mit `Part of MIR-XX` taggen (Work in Progress) oder `Fixes MIR-XX` (abgeschlossen)
- Nach Abschluss: Issue-Status via MCP auf Done setzen

Ausführliche Doku: [docs/linear-workflow.md](docs/linear-workflow.md)

## Roadmap

Detaillierte Roadmap: [ROADMAP.md](ROADMAP.md)

Aktueller Stand: v0.2.0 — Core-Pipeline funktioniert. Nächste Meilensteine:
- v0.3.0: Stabilität, Python 3.12+ Kompatibilität
- v0.4.0: Search/Retrieval-Verbesserungen
- v0.5.0: Multi-Model-Support (Model-Router, vLLM-Backend, Benchmarking)

## Sprache

Alle Kommunikation auf Deutsch. Code-Kommentare und technische Bezeichner bleiben Englisch.
