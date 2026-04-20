# Linear-Workflow für MiroFish-Offline

## Setup-Übersicht

| Was | Wert |
|---|---|
| Workspace | prodoc-digital |
| Team | MiroFish (Key: `MIR`) |
| Projekt | MiroFish-Offline Fork |
| GitHub-Repo | `PRODOC-Digital-GmbH/MiroFish-Offline` |
| Integration | GitHub Webhook (Repo-Level), seit 2026-04-20 verifiziert |

## Labels

| Label | Farbe | Verwendung |
|---|---|---|
| `bug` | rot | Fehler im Code |
| `enhancement` | blau | Verbesserung / neues Feature |
| `upstream-diff` | lila | Bewusste Abweichung vom Upstream |
| `dx` | grün | Developer Experience (Logging, Tooling, Config) |

## Prioritäten

Linear-Standard: `Urgent` (1), `High` (2), `Medium`/Normal (3), `Low` (4).

## Git ↔ Linear Integration

### Magic Words in Commit-Messages

Linear erkennt Issue-Keys in Commit-Messages und verknüpft automatisch:

| Syntax | Wirkung |
|---|---|
| `Part of MIR-123` | Verknüpft Commit mit Issue, setzt Status auf **In Progress**, weist Assignee zu |
| `Fixes MIR-123` | Verknüpft + setzt Status auf **Done** nach Merge |
| `Closes MIR-123` | Wie `Fixes` |
| `Ref MIR-123` | Nur Verknüpfung, kein Statuswechsel |

**Empfehlung:** `Part of MIR-XX` für Work-in-Progress-Commits, `Fixes MIR-XX` nur im finalen Commit oder PR-Title.

### Branch-Naming

Linear schlägt Branch-Namen vor (z.B. `sweimar/mir-13-debug-logging-im-llm-client`). Diese sind optional — die Integration arbeitet über Commit-Messages, nicht Branch-Namen.

### Was passiert automatisch?

Wenn ein Commit mit Magic Word gepusht wird:
1. Commit erscheint als **Attachment** im Linear-Issue (mit Link zum GitHub-Commit)
2. Issue-Status wechselt je nach Magic Word
3. Assignee wird auf den Commit-Autor gesetzt

## Workflow für Claude-Sessions

### Vor der Implementierung

1. Relevantes Linear-Issue identifizieren (z.B. `MIR-8`)
2. Issue-Details via MCP abrufen: `mcp__linear__get_issue` mit `id: "MIR-8"`
3. Ggf. Status auf **In Progress** setzen

### Während der Implementierung

- Commits mit `Part of MIR-XX` im Message-Body taggen
- Bei mehreren Issues pro Session: jeden Commit dem richtigen Issue zuordnen

### Nach der Implementierung

- Issue-Status auf **Done** setzen via `mcp__linear__save_issue` mit `state: "Done"`
- Oder `Fixes MIR-XX` im letzten Commit / PR-Title verwenden

### Neue Issues anlegen

```
mcp__linear__save_issue:
  team: "MiroFish"
  project: "MiroFish-Offline Fork"
  title: "Kurzer, prägnanter Titel"
  labels: ["bug"]          # oder enhancement, dx, upstream-diff
  priority: 3              # 1=Urgent, 2=High, 3=Medium, 4=Low
  description: "Markdown-Beschreibung"
```

## MCP-Toolübersicht

| Tool | Zweck |
|---|---|
| `mcp__linear__list_issues` | Issues auflisten (mit Filtern) |
| `mcp__linear__get_issue` | Einzelnes Issue mit Attachments abrufen |
| `mcp__linear__save_issue` | Issue erstellen (ohne `id`) oder updaten (mit `id`) |
| `mcp__linear__list_issue_labels` | Verfügbare Labels abrufen |
| `mcp__linear__list_projects` | Projekte auflisten |

## Aktueller Backlog (Stand 2026-04-20)

| Key | Titel | Prio | Labels |
|---|---|---|---|
| MIR-5 | Graph-Memory-Updater DI-Bug | Medium | bug |
| MIR-6 | Report-Agent Interview-Timeout | Medium | bug |
| MIR-7 | Chunker splittet mitten im Wort | Low | bug |
| MIR-8 | Vektor-Dimensionen konfigurierbar machen | High | enhancement |
| MIR-9 | Agent-Aktivitätszeiten auf deutsche Zeitzonen | Medium | enhancement, upstream-diff |
| MIR-10 | Config-Generator Bias reduzieren | Low | enhancement, upstream-diff |
| MIR-11 | Auto-Export Report | High | enhancement |
| MIR-12 | Auto-Export Agent-Personas + Configs | High | enhancement |
| MIR-13 | Debug-Logging im LLM-Client | Low | dx |
| MIR-14 | num_ctx + extra_body in allen 3 LLM-Call-Stellen | Medium | dx |

> **Hinweis:** Diese Tabelle ist ein Snapshot. Für den aktuellen Stand immer `mcp__linear__list_issues` mit `team: "MiroFish"` abfragen.
