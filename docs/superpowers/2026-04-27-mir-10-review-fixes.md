# MIR-10 Review Fixes — Implementation Plan

Aus dem Code-Review der MIR-10 Implementierung (Config Generator Bias).
6 Fixes, nach Priorität sortiert.

## Fix 1: PATCH-Endpoint Input-Validierung (B2)

**Datei:** `backend/app/api/simulation.py` — `patch_simulation_config()` (~Zeile 1312)

**Problem:** `discussion_topics` wird ohne Type-Check oder Längenlimit gespeichert.

**Änderung:** Nach `if "discussion_topics" in data:` einfügen:

```python
topics = data["discussion_topics"]
if not isinstance(topics, str):
    return jsonify({"success": False, "error": "discussion_topics must be a string"}), 400
if len(topics) > 10000:
    return jsonify({"success": False, "error": "discussion_topics too long (max 10000 chars)"}), 400
config["event_config"]["narrative_direction"] = topics
```

Statt dem bisherigen direkten `data["discussion_topics"]` Zugriff.

---

## Fix 2: Toggle nach Prepare disablen (F2)

**Datei:** `frontend/src/components/Step2EnvSetup.vue`

**Problem:** Der Narrative-Mode-Toggle bleibt nach abgeschlossener Preparation interaktiv, Änderungen haben aber keinen Effekt.

**Änderung im Template** (im `<input>` des Toggles):

```html
<input type="checkbox" v-model="useGuidedNarrative" :disabled="phase > 1">
```

**Zusätzlich:** Disabled-Hint anzeigen wenn `phase > 1`:

```html
<p class="description hint" v-if="phase > 1">{{ $t('step2.narrativeModeLockedHint') }}</p>
```

**Locale-Keys ergänzen:**
- `en.json`: `"step2.narrativeModeLockedHint": "Narrative mode was set at preparation time. Re-prepare to change."`
- `de.json`: `"step2.narrativeModeLockedHint": "Narrativ-Modus wurde bei der Vorbereitung festgelegt. Erneut vorbereiten um zu ändern."`

---

## Fix 3: Fallback-Dict mode-aware machen (B1)

**Datei:** `backend/app/services/simulation_config_generator.py` — `_generate_event_config()` (~Zeile 731)

**Problem:** Fallback-Dict nutzt immer `narrative_direction` als Key, auch im neutral-Mode.

**Änderung:**

```python
topic_key = "narrative_direction" if narrative_mode == "guided" else "discussion_topics"
return {
    "hot_topics": [],
    topic_key: "",
    "initial_posts": [],
    "reasoning": "Using default configuration"
}
```

Die Methode hat bereits `narrative_mode` als Parameter, der Zugriff ist also direkt möglich.

---

## Fix 4: narrative_mode Default im PATCH setzen (B4)

**Datei:** `backend/app/api/simulation.py` — `patch_simulation_config()` (~Zeile 1315)

**Problem:** Alte Configs ohne `narrative_mode` werden ohne Default zurückgeschrieben.

**Änderung:** Nach der `discussion_topics`-Aktualisierung:

```python
config["event_config"].setdefault("narrative_mode", "neutral")
```

---

## Fix 5: Dead-Code `res.success` entfernen (F1)

**Datei:** `frontend/src/components/Step2EnvSetup.vue` — `saveTopics()` (~Zeile 783)

**Problem:** Axios-Interceptor unwrapped die Response, `res.success` ist immer true wenn kein Error.

**Änderung:** `saveTopics()` vereinfachen:

```javascript
const saveTopics = async () => {
  try {
    await patchSimulationConfig(props.simulationId, {
      discussion_topics: editedTopics.value
    })
    originalTopics.value = editedTopics.value
    addLog('Discussion topics updated')
  } catch (err) {
    addLog(`Failed to save topics: ${err.message}`)
  }
}
```

---

## Fix 6: CSS für disabled Toggle-State (F2 Ergänzung)

**Datei:** `frontend/src/components/Step2EnvSetup.vue` — `<style>` Abschnitt

**Änderung:** CSS für disabled Checkbox ergänzen:

```css
.switch-control input:disabled + .switch-track {
  opacity: 0.4;
  cursor: not-allowed;
}
```

---

## Verifikation nach Umsetzung

1. Syntax-Check: alle geänderten Dateien fehlerfrei
2. Step2 laden → Toggle sichtbar, umschaltbar vor Prepare
3. Prepare starten → Toggle wird disabled, Hint erscheint
4. Discussion Topics editieren → Save/Reset funktioniert
5. Save mit leerem String → akzeptiert (leerer String ist valider Input)
6. Save mit nicht-String (manueller curl-Test) → 400 Error
7. Alte simulation_config.json ohne narrative_mode laden → kein Crash
