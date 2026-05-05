---
name: update-tech-report
description: Use when the user wants to update or extend the central project documentation (`docs/technical-report-benchmark-2026-04.md`) with insights from the current chat session. Trigger phrases include "update tech report", "ergänze den technical report", "/update-tech-report", "Erkenntnisse in den Report einarbeiten". Reads the report fully, walks the chat for new findings (review insights, benchmarks, ticket changes, architecture/limitation gaps, contributor patterns), and writes targeted edits plus a Changelog entry — without rewriting the whole file or breaking the existing tone.
---

# Update Tech Report

Du hast Zugriff auf den technischen Report unter `docs/technical-report-benchmark-2026-04.md`. Dieser Report dokumentiert das Simulab-Projekt (ehemals MiroFish-Offline) und wird über mehrere Chat-Sessions hinweg gepflegt. Deine Aufgabe ist, den Report mit Informationen aus der **aktuellen** Chat-Session zu ergänzen.

## Vorgehen

**1. Lies den Report zuerst vollständig.** Verstehe die Struktur (10 Hauptabschnitte + Anhang + Changelog), den Stil (technisch-sachlich, deutsch, viele Markdown-Tabellen) und welche Themen schon abgedeckt sind.

**2. Gehe den gesamten Chatverlauf dieser Session systematisch durch.** Prüfe folgende vier Bereiche:

### A. Review-Erkenntnisse
- Welche Code-Quality-Issues wurden im Review gefunden?
- Welche Security-Fixes wurden gemacht? (XSS, Cypher Injection, etc.)
- Welche Architektur-Empfehlungen wurden gegeben?
- Gab es Performance-Erkenntnisse aus dem Review?

### B. Benchmark- und Test-Erkenntnisse
- Wurden Benchmark-Runs in der Session besprochen oder neu durchgeführt?
- Gibt es zusätzliche Daten zu Modell-Vergleichen?
- Wurden Quality-Score-Formeln diskutiert oder angepasst?
- Gibt es Erkenntnisse zur Post-Qualität, die im Report fehlen?
- Neue Sprach-/i18n-Beobachtungen (z.B. Sprach-Anteile pro Output-Typ)?
- Gibt es einen neuen Test-Run, der in die Pipeline-Timing-Tabelle (4.2) und/oder den Anhang gehört?

### C. Überprüfung bestehender Aussagen
- Stimmen die Ticket-Beschreibungen (Abschnitt 2.1 / 2.2) mit dem überein, was tatsächlich implementiert und reviewt wurde?
- Sind die Verhaltens-Erkenntnisse (Abschnitt 5) korrekt und vollständig?
- Fehlen Limitationen (Abschnitt 9.4), die in der Session aufgefallen sind?
- Stimmen die Architektur-Beschreibungen (Abschnitt 6)?
- Wurden Linear-Tickets erstellt, geschlossen oder umnummeriert? Cross-References im Report konsistent halten.

### D. Fehlende technische Details
- Gibt es Code-Patterns oder Architektur-Entscheidungen, die für Contributors wichtig wären (Abschnitt 10.5 — "Security-relevante Code-Patterns")?
- Wurden in der Session Risiken identifiziert, die im Report erwähnt werden sollten?
- Gibt es Empfehlungen für zukünftige Entwicklung?

## Ausgabeformat

Ergänze den Report **direkt** in `docs/technical-report-benchmark-2026-04.md`. Mache folgendes:

- **Bestehende Abschnitte erweitern**, wo Informationen fehlen (Tabellen-Zeilen, Listen-Items, Kurzanmerkungen).
- **Neue Unterabschnitte nur**, wo wirklich ein neues Thema abgedeckt wird (das nicht in einen existierenden Abschnitt passt).
- **Widersprüche korrigieren** mit einem kurzen Kommentar, was geändert wurde.
- **Am Ende des Reports den Changelog-Abschnitt ergänzen:** `- [Datum] — Ergänzungen aus [Session-Beschreibung]: [Stichpunkte was hinzugefügt wurde, Sub-Bullets je Abschnitt]`

**Wichtig:**
- **Nicht den gesamten Report umschreiben.** Nur gezielt ergänzen und korrigieren.
- **Stil konsistent halten:** technisch-sachlich, deutsch, Markdown-Tabellen wo sinnvoll, keine Emojis (außer ✓/⚠/✗ in Validierungs-Tabellen wo schon etabliert).
- **Cross-Referenzen pflegen:** Wenn neue Tickets erwähnt werden, zu MIR-Nummern verlinken; wenn Files genannt werden, mit Pfad und ggf. Zeilennummer (`backend/app/services/...py:123`).
- **Datumsangaben absolut**, nicht relativ ("2026-05-04", nicht "gestern").

## Verifikation

Nach den Edits:

1. `wc -l docs/technical-report-benchmark-2026-04.md` zeigt mehr Zeilen als vorher (typisch +50 bis +100 pro Session)
2. Changelog ist letzter Abschnitt vor EOF, neuer Eintrag mit aktuellem Datum ist drin
3. Markdown-Syntax bleibt valide: `python3 -c "import markdown; markdown.markdown(open('docs/technical-report-benchmark-2026-04.md').read())"` läuft schweigend durch
4. Alle Cross-References zu MIR-Tickets sind aktuell (`grep "MIR-" docs/technical-report-benchmark-2026-04.md` → keine erfundenen Nummern)

## Beispiel-Aufruf

> "Lies dir den Report durch, gehe den Chatverlauf durch und ergänze den Report mit den heutigen Erkenntnissen."

→ Vollständigen Workflow ausführen: Report lesen, Chat durchgehen (4 Bereiche), Edits gezielt setzen, Changelog-Eintrag schreiben, Verifikations-Checks am Ende kurz auflisten.
