
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

## Google Authentication and Snapshot Fallback

For Google Calendar import:

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
deterministically to the validating orchestrator instead.

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
