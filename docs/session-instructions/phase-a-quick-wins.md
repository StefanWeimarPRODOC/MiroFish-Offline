# Phase A — Quick-Wins vor dem ministral-Test mit deutschen Seeds

> Erstellt: 2026-05-06 — gedacht als Briefing für eine eigene Implementierungs-Session.
> Zugehöriger Test-Run kommt in Phase B (siehe [phase-a-code-review.md](phase-a-code-review.md) für den Zwischen-Review).

## Kontext

Der letzte Test-Run (`sim_2b5664458700`, qwen2.5:32b Q4 mit `OUTPUT_LANGUAGE=Deutsch`) hat MIR-23 und MIR-24 validiert (Commit `b0f5d07`) und 7 neue Folge-Tickets aufgedeckt. Vier davon sind **Quick-Wins** mit hoher Wirkung auf den nächsten geplanten Test-Run (ministral-3:14b mit ausführlichen deutschen Seed-Dokumenten):

- **MIR-26** Ollama Modell-Eviction → macht Persona-Generierung 3-5× schneller
- **MIR-27** Persona-Routing-Default → Custom Entity-Types werden korrekt als Person/Group erkannt
- **MIR-25** `requestWithRetry` retried 4xx → 7s-Verzögerung bei 409-Lock weg
- **MIR-31** Cypher-Label-Sanitize zu rigide → Multi-Word-Labels gehen nicht mehr verloren

Alle vier sind in unter 4h Code-Aufwand machbar und sollen **als ein gemeinsamer Commit** (oder mehrere kleine, je nach Stil) auf einen Feature-Branch gehen, der dann separat reviewt wird.

## Reihenfolge & Aufwand

| # | Ticket | Aufwand | Datei(en) |
|---|---|---|---|
| 1 | MIR-26 — `keep_alive: 30m` pro Request | ~1h | 3 LLM-Call-Stellen (siehe unten) |
| 2 | MIR-27 — Persona-Routing-Heuristik | ~1h | `oasis_profile_generator.py` |
| 3 | MIR-31 — Label-Sanitize normalisieren | ~30min | `neo4j_storage.py` |
| 4 | MIR-25 — `requestWithRetry` skip 4xx | ~30min | `frontend/src/api/index.js` |

Empfohlene Reihenfolge: 1 → 2 → 3 → 4 (von größtem Effekt auf den nächsten Test zu kleinstem).

---

## MIR-26 — Ollama `keep_alive: 30m` pro Request

### Problem
`qwen2.5:32b` wird zwischen Embedding-Calls und LLM-Calls aus dem RAM evictet trotz `OLLAMA_MAX_LOADED_MODELS=3` (`ollama ps` zeigt `Stopping...`). Default `OLLAMA_KEEP_ALIVE=5min` ist zu kurz für die Pipeline-Cadence + LRU-Verdrängung durch Embedding-Calls. Effekt: ~80s/Persona statt ~10-30s.

### Lösung
`keep_alive`-Parameter pro LLM-Request setzen — robuster als globale Env-Variable (überlebt Restart, kein User-System-Eingriff).

### Files (alle drei Stellen, identisches Pattern wie MIR-14)
- `backend/app/services/llm_client.py` — Haupt-LLM-Client (zentraler Wrapper)
- `backend/app/services/simulation_config_generator.py` — eigener OpenAI-Client
- `backend/app/services/oasis_profile_generator.py` — eigener OpenAI-Client

### Vorgehen
- In allen drei Files an den `client.chat.completions.create(...)`-Aufrufen `extra_body` erweitern. Aktuell wird dort schon `num_ctx` gesetzt (siehe MIR-14):
  ```python
  extra_body={"options": {"num_ctx": self._num_ctx}}
  ```
- Erweitern um `keep_alive`:
  ```python
  extra_body={"options": {"num_ctx": self._num_ctx}, "keep_alive": "30m"}
  ```
- Wert konfigurierbar machen: `Config.OLLAMA_KEEP_ALIVE` (Default `"30m"`) in `backend/app/config.py`. Über `.env` überschreibbar.
- Nur bei Ollama-Backend setzen — bei anderen OpenAI-kompatiblen APIs ignoriert ein unbekannter Parameter zwar meist, aber sicher ist sicher. `_is_ollama()`-Check existiert bereits.

### Verifikation
1. Pipeline-Run starten, parallel `watch -n 5 'ollama ps'` im Terminal.
2. **Erwartung:** `qwen2.5:32b` zeigt `UNTIL: ~30 minutes from now` (oder ähnlich), nicht `Stopping...`.
3. Persona-Phase-Dauer im `timing.json` vergleichen: `avg_persona_seconds` sollte von ~43s auf <20s fallen.

---

## MIR-27 — Persona-Routing-Heuristik für Custom Entity-Types

### Problem
`oasis_profile_generator.py:170-179` definiert nur generische Upstream-Typen in den hardcoded Listen (`student, person, university, ngo, ...`). Custom Entity-Types aus der Ontologie-Generierung (`Diabetologist`, `KOLDiabetology`, `NovaSulinSalesRep`, `DiabetesPatient`, `Medication`, `Location`) tauchen in keiner der beiden Listen auf → der `else`-Branch in [oasis_profile_generator.py:464-473](../../backend/app/services/oasis_profile_generator.py#L464-L473) defaultet zu Group-Persona. Beobachtbarer Bug: `DiabetesPatient` wurde als "Organisation 'DiabetesPatient' ist eine virtuelle Instanz..." beschrieben.

### Lösung
Heuristische Erweiterung in `_is_individual_entity` und `_is_group_entity`. Substring-Match:

- **Individual-Indikatoren:** `*patient*`, `*doctor*`, `*physician*`, `*nurse*`, `*rep*`, `*kol*`, `*expert*`, `*ist$` (Pluralformen wie `Diabetologist`, `Specialist`)
- **Group-Indikatoren:** `*ag$`, `*gmbh$`, `*verband*`, `*kasse*`, `*inc$`, `*corp*`, `*ngo*`, `*hospital*`, `*klinik*`, `*verein*`

Bei Unentscheidbarkeit (kein Substring-Match): **Default-Fallback auf Individual** statt Group (Person ist die häufigere realistische Annahme, ein Mensch der mit einem Account-Profil-Text beschrieben wird ist auffälliger als umgekehrt).

### Files
- `backend/app/services/oasis_profile_generator.py:440-446` — `_is_individual_entity` und `_is_group_entity` erweitern
- `backend/app/services/oasis_profile_generator.py:464-473` — Routing-Logik um Default-Fallback ergänzen
- Neue Tests in `backend/tests/services/test_oasis_profile_generator.py` falls Test-Setup vorhanden — sonst Smoke-Test inline

### Vorgehen
- Listen `INDIVIDUAL_ENTITY_TYPES` und `GROUP_ENTITY_TYPES` belassen (Backwards-Compat für exakte Matches)
- Zusätzliche Substring-Heuristiken in den `_is_*`-Methoden
- `_generate_profile_with_llm`: Wenn weder individual noch group → in Log-Warning vermerken (`logger.warning(f"Unknown entity_type '{entity_type}', defaulting to individual")`) und Individual rendern
- Optional aber empfohlen: Eine `cardinality`-Spalte in den Test-Run-Personas dokumentieren, damit beim nächsten Test direkt sichtbar ist welcher Branch genommen wurde

### Verifikation
- Unit-Tests: `assert _is_individual_entity('DiabetesPatient') is True`, `assert _is_group_entity('GKV-Verband') is True`, etc.
- Im Test-Run: In `reddit_profiles.json` prüfen, dass `patient_*`, `doctor_*`, `kol_*`-Personas Individual-Style haben (Background, Personality, Core positions etc. — nicht "Die Organisation X ist eine virtuelle Instanz")

---

## MIR-31 — Cypher-Label-Sanitize: Normalisieren statt Rejecten

### Problem
`_sanitize_label()` in `backend/app/storage/neo4j_storage.py` weist Labels mit Sonderzeichen, Spaces oder Mixed-Language ab statt sie zu normalisieren. Im letzten Test-Run gingen 3 valide Entities verloren: `Medication/Drug` (Slash), `Typical Advisory Board Problem` (Spaces), `Key Opinion Leader in Diabetologie` (Spaces + Mixed-Lang).

### Lösung
Statt Reject: Label normalisieren (Spaces/Slashes → Underscore, Sonderzeichen entfernen, Digit-Prefix vorsetzen).

```python
def _sanitize_label(label: str) -> str:
    if not label:
        return None  # weiterhin reject bei komplett leerem Input
    # 1. Spaces, Slashes, Bindestriche → Underscore
    label = re.sub(r'[\s/\-]+', '_', label.strip())
    # 2. Diakritika belassen oder ASCII-fold (Entscheidung: belassen, Cypher unterstützt Unicode in Backticks)
    #    Hier: ASCII-Letters + Digits + Underscore + Umlaute durchlassen
    label = re.sub(r'[^A-Za-z0-9_äöüÄÖÜß]', '', label)
    # 3. Kein Leading-Digit: Prefix
    if not label or not label[0].isalpha():
        label = f'L_{label}' if label else None
    return label
```

**Wichtig:** Cypher braucht für Labels mit Sonderzeichen Backticks (`` `Medication_Drug` ``). Prüfe in den Aufruf-Stellen, ob das schon der Fall ist — wenn Labels weiterhin als f-string in Cypher interpoliert werden, MUSS der Aufrufer sie in Backticks setzen oder die Sanitize-Funktion gibt nur ASCII zurück.

**Sicherer Default (Empfehlung):** ASCII-only zurückgeben, dann sind Backticks nicht nötig. Umlaute mappen (ä→ae, ö→oe, ü→ue, ß→ss).

### Files
- `backend/app/storage/neo4j_storage.py:_sanitize_label()`
- Aufruf-Stellen suchen via `grep -rn "_sanitize_label" backend/` und prüfen ob Backticks benötigt werden

### Verifikation
- Unit-Tests:
  - `_sanitize_label("Medication/Drug") == "Medication_Drug"`
  - `_sanitize_label("Typical Advisory Board Problem") == "Typical_Advisory_Board_Problem"`
  - `_sanitize_label("Key Opinion Leader in Diabetologie") == "Key_Opinion_Leader_in_Diabetologie"` (oder mit Umlaut-Mapping)
  - `_sanitize_label("123Medication") == "L_123Medication"`
  - `_sanitize_label("") is None`
- Im Test-Run: Logs auf `Rejected unsafe Cypher label` prüfen — sollte 0 Treffer geben

---

## MIR-25 — `requestWithRetry` retried 4xx-Antworten

### Problem
`frontend/src/api/index.js:54-65` retried alle Fehler 3× mit exponentiellem Backoff (1s + 2s + 4s = ~7s). Auch 4xx-Status-Codes wie 409 (Concurrent-Lock aus MIR-23) werden retried — bringt nichts, der Server lehnt aus Logik-Gründen ab. Status: bereits "In Progress".

### Lösung
4xx-Fehler nicht retryen. Nur 5xx und Network-Errors (timeout, ECONNABORTED, network-disconnect) retryen.

```javascript
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn()
    } catch (error) {
      // 4xx: Client-Fehler — kein Retry, Server hat aus Logik-Gründen abgelehnt
      const status = error?.response?.status
      if (status && status >= 400 && status < 500) {
        throw error
      }
      if (i === maxRetries - 1) throw error
      console.warn(`Request failed (status: ${status || 'network'}), retrying (${i + 1}/${maxRetries})...`)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}
```

### Files
- `frontend/src/api/index.js:54-65` — `requestWithRetry`-Funktion

### Verifikation
- Backend manuell triggern, dass es 409 zurückgibt (z.B. zwei Reports parallel starten via `curl`)
- Frontend-Network-Tab beobachten: 409-Response, **nur 1 Request**, kein 7s-Delay

---

## Branch & Commit-Workflow

- Neuer Branch: `sweimar/mir-26-phase-a-quickwins` (oder ähnlich, Linear-Style optional)
- Empfohlen: **ein Commit pro Ticket**, alle vier auf den gleichen Branch — dann ist der Code-Review (siehe [phase-a-code-review.md](phase-a-code-review.md)) klar pro Ticket strukturiert
- Commit-Messages mit Magic Words: `Fixes MIR-26`, `Fixes MIR-27`, etc. — das setzt die Tickets nach Merge automatisch auf Done
- Alternative: ein gesammelter Commit mit `Fixes MIR-25, MIR-26, MIR-27, MIR-31` im Body

## Test-Vorbereitung nach Phase A

Nach erfolgreichem Code-Review und Merge:
1. Container Rebuild: `docker compose up -d --build mirofish` (laut Memory: Rebuild statt Restart wenn `.env` geändert wurde — relevant falls neue `OLLAMA_KEEP_ALIVE`-Config dort landet)
2. Ollama-Status prüfen: `OLLAMA_NUM_PARALLEL=3`, `OLLAMA_MAX_LOADED_MODELS=3` sollten weiterhin gesetzt sein
3. `.env`-Switch auf `LLM_MODEL_NAME=ministral-3:14b-mirofish` (oder Q4-Variante)
4. Deutsche Seed-Dokumente bereitlegen
5. Test-Run starten — Phase B beginnt

## Verwandt

- Memory: `~/.claude/projects/.../memory/project_ollama_keep_alive_optimization.md` (MIR-26 Hintergrund)
- Memory: `~/.claude/projects/.../memory/project_persona_routing_and_compliance.md` (MIR-27 + MIR-28 Hintergrund)
- Technical Report Abschnitt 9.4 Limitationen (10-16) listet alle 7 Folge-Tickets aus der letzten Session
- Code-Review-Anweisung: [phase-a-code-review.md](phase-a-code-review.md)
