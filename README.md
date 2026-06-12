# Agentischer Kalenderoptimierer

Dieser Prototyp importiert eine Kalenderwoche, analysiert sie mit
[Agent Squad](https://github.com/2FastLabs/agent-squad) und lokalen Ollama-Modellen und
erzeugt einen beratenden Markdown-Report. Das System besitzt keine Funktion zum Schreiben,
Verschieben oder Löschen von Google-Kalenderterminen.

## Starten

Der empfohlene Start erfolgt im Projekt-Root:

```powershell
cd C:\Users\Windoofpedia\Desktop\uni\AgenticSystemProject
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m calendar_optimizer.run
```

`src/calendar_optimizer/run.py` wird nicht direkt ausgeführt. Das Projekt verwendet eine
`src`-Paketstruktur und wird deshalb über `python -m calendar_optimizer.run` gestartet.
Nach dem Editable-Install funktioniert dieser Modulaufruf auch aus anderen Verzeichnissen;
die Standardpfade für `credentials.json`, `.secrets`, `snapshots` und `reports` zeigen weiterhin
auf den Projekt-Root.

Der Standardlauf versucht, die aktuelle Woche aus Google Calendar zu importieren. Für den ersten
Google-Import muss `credentials.json` im Projekt-Root liegen. Falls bereits ein Snapshot existiert,
wird dieser bei fehlender Authentifizierung automatisch verwendet. Ollama muss in beiden Fällen mit
den benötigten Modellen gestartet sein.

Während des Laufs zeigt die Konsole den Agentenflow an:

```text
[FLOW] Agent Squad -> Calendar Orchestrator: Anfrage geroutet
[FLOW] Calendar Orchestrator -> Schedule Manager, HR Planner, Traffic Optimizer: Woche parallel analysieren
[FLOW] Schedule Manager arbeitet mit qwen2.5:14b-instruct-q5_K_M
[FLOW] Schedule Manager -> Tool list_events: {}
[FLOW] Tool list_events -> Schedule Manager: Ergebnis erhalten
[FLOW] Calendar Orchestrator: Empfehlung 'Ausgewogen' gewählt
```

## Google-Authentifizierung und Snapshot-Fallback

Für den Google-Import:

1. Google Calendar API im Google-Cloud-Projekt aktivieren.
2. Einen OAuth-Client vom Typ „Desktop-App“ erstellen.
3. Die heruntergeladene Datei als `credentials.json` im Projekt-Root ablegen.
4. Die eigene Google-Adresse beim OAuth-Testmodus als Testnutzer eintragen.
5. `python -m calendar_optimizer.run` starten und den Browser-Dialog bestätigen.

Der Zugriff verwendet ausschließlich `calendar.events.readonly`. Nach jedem erfolgreichen
Google-Login wird der OAuth-Token unter `.secrets/google-token.json` gespeichert. Beim ersten
erfolgreichen Google-Import speichert das Programm außerdem einmalig einen lokalen Snapshot:

```text
snapshots/latest.json
```

Ein bestehender Snapshot wird bei späteren Google-Importen nicht überschrieben. Damit verwenden
alle Offline- und Fallback-Läufe dauerhaft denselben Kalenderstand.

Wenn Google OAuth nicht eingerichtet ist, abgelehnt wird oder der Google-Import fehlschlägt,
verwendet der Standardlauf automatisch diesen Snapshot. Existiert noch kein Snapshot, muss zuerst
ein erfolgreicher Google-Import durchgeführt oder ein Snapshot über die Python-Funktion gespeichert
werden:

```python
from pathlib import Path
from calendar_optimizer.integrations.snapshot import save_calendar_snapshot

save_calendar_snapshot(calendar, Path("snapshots/latest.json"))
```

Ein vorhandener Snapshot kann ohne Google-Authentifizierung ausdrücklich gestartet werden:

```powershell
python -m calendar_optimizer.run --source snapshot
```

Ein Snapshot enthält genau die beim Speichern importierte Woche; `--week-start` verändert dessen
Inhalt nicht. Der Snapshot enthält private Kalenderdaten und wird deshalb durch `.gitignore`
ausgeschlossen.

## Agenten

| Agent | Lokales Modell | Aufgabe |
|---|---|---|
| Orchestrator | `llama3.1:8b` | Koordination und Auswahl einer validierten Variante |
| Schedule Manager | `qwen2.5:14b-instruct-q5_K_M` | Verschiebbarkeit schätzen und drei Varianten vorschlagen |
| HR Planner | `llama3.1:8b` | Pausen, Mahlzeiten und Belastung bewerten |
| Traffic Optimizer | `llama3.1:8b` | Ortswechsel mit konservativen Puffern bewerten |

Andere Modellnamen werden zur Laufzeit abgelehnt. Der eingebaute Agent-Squad-Supervisor wird
nicht verwendet, weil er keine lokalen OpenAI-kompatiblen Ollama-Agenten unterstützt. Agent Squad
routet stattdessen deterministisch zum validierenden Orchestrator.

## Installation

Voraussetzungen: Python 3.11 oder neuer sowie [Ollama](https://ollama.com/).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .

ollama pull qwen2.5:14b-instruct-q5_K_M
ollama pull llama3.1:8b
ollama serve
```

Ollama muss unter `http://localhost:11434` erreichbar sein. Sämtliche LLM-Aufrufe bleiben lokal.

## Demo mit JSON

Die Beispieldaten liegen in der Woche ab Montag, dem 8. Juni 2026:

```powershell
python -m calendar_optimizer.run `
  --source json `
  --input-json examples/sample_calendar.json `
  --week-start 2026-06-08
```

Der Report wird standardmäßig als `reports/week-2026-06-08.md` gespeichert.

## CLI-Optionen

```text
--source google|json|snapshot
--input-json PATH
--calendar-id ID
--week-start YYYY-MM-DD
--timezone IANA_ZONE
--credentials PATH
--token PATH
--snapshot PATH
--day-start HH:MM
--day-end HH:MM
--output PATH
```

Die Standardzeitzone ist `CALENDAR_TIMEZONE` oder `Europe/Berlin`; das Tagesfenster ist
`07:00–22:00`.

## Sicherheits- und Validierungsregeln

- Ganztägige Termine werden nie verschoben.
- Unbekannte Termine, Daueränderungen, Konflikte und Vorschläge außerhalb der Woche werden verworfen.
- Varianten mit verbleibenden bestehenden Terminkonflikten werden vollständig verworfen.
- Falls Agenten keine konfliktfreie Variante liefern, wird deterministisch eine konfliktfreie
  Vorschlagsvariante erzeugt. Ist dies innerhalb der Woche unmöglich, wird kein Report erzeugt.
- Verschiebbarkeit wird vom Modell geschätzt und im Report mit Konfidenz gekennzeichnet.
- Reisezeiten verwenden keine Maps-API: unbekannter Ort 15 Minuten, physisch/virtuell 20 Minuten,
  verschiedene physische Orte 30 Minuten.
- Der erzeugte Report weist ausdrücklich darauf hin, dass keine Kalenderänderungen vorgenommen wurden.

## Tests

```powershell
pytest
```

Die Tests verwenden gemockte LLM- und Google-Antworten. Ein manueller Smoke-Test mit Ollama und
Google OAuth ist optional.
