# Agentischer Kalenderoptimierer

Dieser Prototyp importiert eine Kalenderwoche, analysiert sie mit
[Agent Squad](https://github.com/2FastLabs/agent-squad) und lokalen Ollama-Modellen und
erzeugt einen beratenden Markdown-Report. Das System besitzt keine Funktion zum Schreiben,
Verschieben oder Löschen von Google-Kalenderterminen.

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

## Google Calendar read-only einrichten

1. In einem Google-Cloud-Projekt die Google Calendar API aktivieren.
2. Einen OAuth-Client vom Typ „Desktop-App“ erstellen.
3. Die heruntergeladene Client-Datei als `credentials.json` im Projekt ablegen.
4. Den ersten Lauf starten und den Browser-Dialog bestätigen.

```powershell
python -m calendar_optimizer.run
```

Der OAuth-Token wird lokal unter `.secrets/google-token.json` gespeichert und von Git ignoriert.
Der einzige angeforderte Scope ist:

```text
https://www.googleapis.com/auth/calendar.events.readonly
```

Es werden expandierte Serientermine der aktuellen lokalen Woche von Montag 00:00 bis zum nächsten
Montag 00:00 importiert. Mit `--week-start YYYY-MM-DD` kann eine andere Woche gewählt werden.

## CLI-Optionen

```text
--source google|json
--input-json PATH
--calendar-id ID
--week-start YYYY-MM-DD
--timezone IANA_ZONE
--credentials PATH
--token PATH
--day-start HH:MM
--day-end HH:MM
--output PATH
```

Die Standardzeitzone ist `CALENDAR_TIMEZONE` oder `Europe/Berlin`; das Tagesfenster ist
`07:00–22:00`.

## Sicherheits- und Validierungsregeln

- Ganztägige Termine werden nie verschoben.
- Unbekannte Termine, Daueränderungen, Konflikte und Vorschläge außerhalb der Woche werden verworfen.
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
