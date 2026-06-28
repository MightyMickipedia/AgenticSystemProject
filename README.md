# Agentischer Kalenderoptimierer

Dieser Prototyp importiert eine Kalenderwoche, analysiert sie mit
[Agent Squad](https://github.com/2FastLabs/agent-squad) und lokalen Ollama-Modellen und
erzeugt einen beratenden Markdown-Report. Das System besitzt keine Funktion zum Schreiben,
Verschieben oder Löschen von Google-Kalenderterminen.

## Starten

### CLI (Kommandozeile)

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m calendar_optimizer.run
```

`src/calendar_optimizer/run.py` wird nicht direkt ausgeführt. Das Projekt verwendet eine
`src`-Paketstruktur und wird deshalb über `python -m calendar_optimizer.run` gestartet.
Nach dem Editable-Install funktioniert dieser Modulaufruf auch aus anderen Verzeichnissen;
die Standardpfade für `credentials.json`, `.secrets`, `snapshots` und `reports` zeigen weiterhin
auf den Projekt-Root.

### Web-Interface

Das Projekt enthält eine vollständige Weboberfläche mit React-Frontend und FastAPI-Backend.

**Backend starten:**

```powershell
python -m pip install -e .
python -m calendar_optimizer.web
```

Das Backend läuft auf **http://localhost:8000**.

**Frontend starten (Entwicklung):**

```powershell
cd frontend
npm install
npm run dev
```

Der Vite-Devserver läuft auf **http://localhost:5173** und leitet API-Aufrufe automatisch
an das Backend weiter.

**Webseite öffnen:** [http://localhost:5173](http://localhost:5173)

**Produktionsbetrieb (einzelner Port):**

```powershell
cd frontend
npm run build
cd ..
python -m calendar_optimizer.web
```

Im Produktionsmodus liefert FastAPI das gebaute Frontend direkt aus.

**Webseite öffnen:** [http://localhost:8000](http://localhost:8000)

### Google-Kalender im Web verbinden

Damit der „Connect Google"-Button funktioniert:

1. `credentials.json` (OAuth-Client „Web-Anwendung") im Projekt-Root ablegen.
2. In der Google Cloud Console als autorisierten Redirect-URI eintragen:
   `http://localhost:8000/api/auth/google/callback`
3. Im **Entwicklungsmodus** (Frontend auf Port 5173) das Backend mit gesetzter
   `FRONTEND_URL` starten, damit der Browser nach dem Login zurück zum Vite-Server
   geleitet wird:

   ```powershell
   $env:FRONTEND_URL = "http://localhost:5173"
   python -m calendar_optimizer.web
   ```

   Im Produktionsmodus (einzelner Port 8000) ist das nicht nötig.

Konfigurierbare Umgebungsvariablen: `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_REDIRECT_URI`,
`FRONTEND_URL`, `CALENDAR_TIMEZONE`. Der Zugriff bleibt schreibgeschützt
(`calendar.events.readonly`); nach dem Login wird die aktuelle Woche aus dem primären
Kalender importiert und der Sitzung zugeordnet.

### Voraussetzungen

- Python 3.11+
- [Ollama](https://ollama.com/) mit den Modellen `llama3.1:8b` und `qwen2.5:14b-instruct-q5_K_M`
- Node.js 18+ (nur für Frontend-Entwicklung)

```powershell
ollama pull llama3.1:8b
ollama pull qwen2.5:14b-instruct-q5_K_M
ollama serve
```

Ollama muss unter `http://localhost:11434` erreichbar sein. Sämtliche LLM-Aufrufe bleiben lokal.

## Google-Authentifizierung (CLI) und Snapshot-Fallback

Für den Google-Import über die CLI:

1. Google Calendar API im Google-Cloud-Projekt aktivieren.
2. Einen OAuth-Client vom Typ „Desktop-App" erstellen.
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
routet stattdessen deterministisch zum validierenden Orchestrator. Enthält die gewählte Woche keine
Termine, wird ohne Modellaufrufe ein deterministischer „Status quo"-Report erzeugt.

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

---

# Agentic Calendar Optimizer (English)

This prototype imports a calendar week, analyzes it using
[Agent Squad](https://github.com/2FastLabs/agent-squad) with local Ollama LLMs, and
produces an advisory Markdown report. The system is **read-only** — it never modifies,
moves, or deletes any Google Calendar events.

## Getting Started

### CLI

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m calendar_optimizer.run
```

The project uses a `src` package layout and must be launched via
`python -m calendar_optimizer.run` (not by running the file directly).

### Web Interface

The project includes a full web UI with a React frontend and FastAPI backend featuring
real-time agent log streaming via WebSocket.

**Start the backend:**

```bash
python -m pip install -e .
python -m calendar_optimizer.web
```

The backend runs at **http://localhost:8000**.

**Start the frontend (development):**

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at **http://localhost:5173** and proxies API calls to the backend
automatically.

**Open in browser:** [http://localhost:5173](http://localhost:5173)

**Production mode (single port):**

```bash
cd frontend
npm run build
cd ..
python -m calendar_optimizer.web
```

In production mode FastAPI serves the built frontend directly.

**Open in browser:** [http://localhost:8000](http://localhost:8000)

### Connecting Google Calendar in the Web UI

For the "Connect Google" button to work:

1. Place `credentials.json` (OAuth client of type "Web application") in the project root.
2. In Google Cloud Console, register the authorized redirect URI:
   `http://localhost:8000/api/auth/google/callback`
3. In **development** (frontend on port 5173), start the backend with `FRONTEND_URL` set so
   the browser is sent back to the Vite dev server after login:

   ```bash
   FRONTEND_URL=http://localhost:5173 python -m calendar_optimizer.web
   ```

   In production (single port 8000) this is not needed.

Configurable environment variables: `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_REDIRECT_URI`,
`FRONTEND_URL`, `CALENDAR_TIMEZONE`. Access stays read-only (`calendar.events.readonly`); after
login the current week is imported from the primary calendar and bound to the session.

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) with models `llama3.1:8b` and `qwen2.5:14b-instruct-q5_K_M`
- Node.js 18+ (frontend development only)

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5:14b-instruct-q5_K_M
ollama serve
```

Ollama must be reachable at `http://localhost:11434`. All LLM calls stay local.

## Google Authentication (CLI) and Snapshot Fallback

For Google Calendar import via the CLI:

1. Enable the Google Calendar API in a Google Cloud project.
2. Create an OAuth client of type "Desktop App".
3. Place the downloaded file as `credentials.json` in the project root.
4. Add your Google address as a test user in the OAuth consent screen.
5. Run `python -m calendar_optimizer.run` and confirm the browser dialog.

Access uses `calendar.events.readonly` only. After a successful Google login the OAuth token
is saved to `.secrets/google-token.json`. On the first successful import a local snapshot is
saved to:

```text
snapshots/latest.json
```

Existing snapshots are not overwritten by later imports, so all offline/fallback runs use the
same calendar data. If Google OAuth is not configured or fails, the default run automatically
uses this snapshot. To run from snapshot explicitly:

```bash
python -m calendar_optimizer.run --source snapshot
```

## Agents

| Agent | Local Model | Task |
|---|---|---|
| Orchestrator | `llama3.1:8b` | Coordination and validated variant selection |
| Schedule Manager | `qwen2.5:14b-instruct-q5_K_M` | Estimate movability and propose three variants |
| HR Planner | `llama3.1:8b` | Evaluate breaks, meals, and workload |
| Traffic Optimizer | `llama3.1:8b` | Evaluate location changes with conservative buffers |

Other model names are rejected at runtime. The built-in Agent Squad supervisor is not used
because it does not support local OpenAI-compatible Ollama agents. Agent Squad routes
deterministically to the validating orchestrator instead. If the selected week has no events,
a deterministic "status quo" report is produced without any model calls.

## Demo with JSON

The sample data is set in the week starting Monday, June 8, 2026:

```bash
python -m calendar_optimizer.run \
  --source json \
  --input-json examples/sample_calendar.json \
  --week-start 2026-06-08
```

The report is saved as `reports/week-2026-06-08.md` by default.

## CLI Options

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

Default timezone is `CALENDAR_TIMEZONE` or `Europe/Berlin`; the day window is `07:00–22:00`.

## Safety and Validation Rules

- All-day events are never moved.
- Unknown events, duration changes, conflicts, and proposals outside the week are discarded.
- Variants with remaining existing conflicts are discarded entirely.
- If agents fail to produce a conflict-free variant, one is generated deterministically.
  If this is impossible within the week, no report is produced.
- Movability is estimated by the model and labeled with confidence in the report.
- Travel times do not use a Maps API: unknown location 15 min, physical/virtual 20 min,
  different physical locations 30 min.
- The generated report explicitly states that no calendar changes were made.

## Web Interface Features

- **Calendar Upload** — drag-and-drop JSON or load from latest snapshot
- **Live Agent Flow Log** — real-time WebSocket streaming of agent activity
- **Visual Week Timeline** — color-coded events with proposed move overlays
- **Optimization Report** — variant cards with proposals, warnings, and recommendations
- **Variant Comparison** — side-by-side timeline view of different optimization variants
- **Google OAuth** — connect Google Calendar directly from the browser

## Tests

```bash
pytest
```

Tests use mocked LLM and Google responses. A manual smoke test with Ollama and Google OAuth
is optional.
