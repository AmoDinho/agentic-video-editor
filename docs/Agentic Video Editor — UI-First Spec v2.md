# Agentic Video Editor — UI-First Spec v2

Oct 12, 2026 · @Amogelang

## Overview

A local-first, UI-first app that turns a folder of raw footage into a rough cut that edits like a reference video. You drop in clips, pick a reference, and an agent reviews everything, cuts it, and stitches it into one watchable video you can export. This spec replaces the v1 build plan's UI and runtime sections and keeps its analysis pipeline, edit decision list (EDL) contract and validator.

**What changes from v1**

- The UI is the product, not a wrapper around a CLI. Every step happens in one workspace.
- Every long-running job shows real progress and an honest time remaining. No indeterminate animated bars.
- The agent produces two or three variants per run, and you pick and refine one.
- You can steer the cut by talking to the agent, editing the transcript, or adjusting the timeline.
- One command starts the whole stack in Docker, with local models using the Mac's GPU.

**Unchanged decisions**

- Footage mixes talking-to-camera and scenic shots with natural sound; both keep their own audio.
- The cut always follows shooting order; the agent chooses what to keep and how long, never the sequence.
- Target machine is a MacBook Pro M3 Pro with 18 GB unified memory.
- Models are local by default and switchable to a cloud model with an API key.
- Out of scope: transitions, animation, graphics, titles, sound effects, music, colour grading.

## What we take from the reference products

| Product | What it does well | What we adopt |
| --- | --- | --- |
| Diffusion Studio | Open-source desktop editor where every edit lives as code an agent can read and write; an infinite canvas to explore, a timeline to sequence; asset browser grouped by camera and source; inspector panel; agent session beside the editor | The EDL stays the single source of truth for agent and UI. Media bin grouped by camera and day. Agent panel docked beside the player. Saved "styles" as reusable presets. |
| Mosaic | Runs edits on autopilot, then A/B tests several variants from the same footage before you drop into a timeline | Each run produces 2–3 variants (tight, reference-matched, relaxed) shown side by side; you pick one, then refine. |
| DreamCut | Transcript-based editing for talking footage | A transcript view where deleting words cuts the video, synced with the timeline. |
| Remotion | React-based video with an embeddable Player and timeline components | Use the Remotion Player to play a cut straight from the EDL in the browser, so edits preview instantly with no render. FFmpeg still does the final export. |
| Renlo | Positions speed as the whole promise | Time-to-first-cut is the headline metric: a first variant should be watchable while analysis is still finishing for later clips. |

**Licensing:** this is a personal project, so Remotion's free licence applies and the Remotion Player is the preview player. Diffusion Studio is open source; read its licence and code in Phase 0 before reusing any part of it.

## The creation flow

The v1 flow made you configure everything, press run, then wait for the whole job before seeing anything. The new flow starts work the moment footage arrives and shows results as they form.

1. **Drop footage.** Drag a folder onto the workspace or pick one from the media library. Analysis starts immediately, clip by clip in shooting order, and each clip's card fills in as it finishes (thumbnail, duration, date shot, talking or scenic, quality flags).
2. **Choose a style.** Pick a reference video, or a style saved from an earlier project. The style shows as a plain-language card, for example "about 9 cuts a minute, most shots 2–5 s, 60% talking, around 8 minutes", so you can see what the agent will aim for.
3. **Add a brief (optional).** One line of direction and a target length. Both have sensible defaults taken from the style.
4. **Generate.** Available as soon as a style is chosen. The agent works front to back in shooting order, waits only for clips it still needs, and the timeline fills in section by section as each is finished.
5. **Compare variants.** Two or three cuts appear as cards (tight, matched, relaxed) with runtime, cut count and a thumbnail strip. Hover to scrub, click to play, pick one.
6. **Refine.** Three ways, all editing the same EDL: ask the agent ("shorter intro", "more of the beach"), delete words in the transcript, or trim, remove and lock segments on the timeline. Every change is a new version you can undo or compare.
7. **Export.** Choose a preset and destination. The render runs in the background with a time-remaining estimate and a notification when done. Also exports a timeline file for Premiere, Resolve or Final Cut.

**Empty and error states** tell you what to do next: an empty project says "Drop a folder of clips to start"; a clip that fails analysis says why ("No audio track", "Unsupported codec: convert to H.264") with a retry button.

## Workspace layout

One screen, four regions, no page changes during normal work. Settings and the project list are the only other screens.

&#91;embedded content: main workspace · wireframe\]

**Top bar:** project name, one status pill that always says what is running and how long is left, and the Export button. Clicking the pill opens the job drawer (see the next section).

**Media bin (left):** clips grouped by day and camera, in shooting order. Each card shows its analysis state; clips can be excluded with one click. Styles (saved references) live in a second tab here.

**Variants and player (centre):** tabs for each variant with its runtime. The player plays the selected variant straight from the EDL, so every edit previews instantly.

**Agent panel (right):** the agent's plan as a checklist, a plain-language feed of what it is doing right now, its time remaining, and a box to ask for changes. Tool calls are summarised in words; a "details" toggle shows the raw log.

**Timeline and transcript (bottom):** the cut as coloured segments sized by duration, talking vs. scenic. Clicking a segment selects it and shows source, in/out and the agent's reason. The Transcript tab shows the same cut as text; striking words removes them.

**Keyboard:** Space play/pause, J/K/L shuttle, Delete removes the selected segment, L locks it, \[ and \] nudge in/out to the next safe cut point, Cmd+Z undo, Cmd+Shift+Z redo. Every change is saved as a version; a version list lets you compare and restore.

## Progress, time remaining and agent activity

In the first build the edit ran behind an endless animated bar with no idea how long was left. The rule now: **no indeterminate loader stays on screen for more than 2 seconds.** Every job shows a percentage, the current step in words, time elapsed and time remaining. While an estimate is still forming, the UI says "Estimating time…" alongside the step count, never just an animation.

**How work is measured.** Every job is split into stages, and every stage counts its work in units it can measure. Rates are measured on this machine, so estimates get better with use.

| Stage | Unit of work | How the estimate is made |
| --- | --- | --- |
| Proxies | Seconds of footage | FFmpeg `-progress` output, exact |
| Shot detection | Seconds of footage | Measured seconds-per-second rate |
| Transcription | Seconds of speech (after silence is removed) | Measured rate for the chosen Whisper model |
| Captions and embeddings | Keyframes | Measured time per keyframe |
| Agent edit | Planned steps: sections × (survey, select, validate), plus revisions | Remaining steps × median step time, plus remaining output tokens ÷ measured tokens per second |
| Preview and export render | Frames | FFmpeg `-progress` output, exact |

**Making estimates trustworthy.** On first launch the app runs a 20-second calibration on a bundled test clip to seed each rate. Rates then update from real runs with a moving average. The shown estimate is smoothed and rounded ("about 6 min"), and it is not allowed to jump up by more than 25% at once without saying why ("Revising: 3 shots need a second look"). For the agent, the plan is known once the outline is written, so the UI shows "Section 3 of 5" and "Revision 1 of up to 4" rather than a guess.

**Job drawer.** Clicking the status pill opens a drawer listing every job with per-stage bars, and buttons to pause, cancel or retry. Finished jobs send a browser notification. Jobs survive a restart: their state lives in the database and they resume from the last finished unit.

**Why the UI never freezes.** All heavy work runs in worker processes, never in the API or the browser. Workers publish progress events to Redis; the API streams them to the browser over server-sent events at most 4 times a second.

## Visual design and UI skills

**Skills for the builder agent to load**

| Skill | Where | Use it for |
| --- | --- | --- |
| frontend-design | Anthropic's public skills (anthropics/skills on GitHub); also built into Claude.ai | Setting the visual direction, type, palette and copy, and avoiding a templated look. Follow its two-pass process: write a token plan, check it against this brief, then build. |
| Remotion Agent Skills | remotion.dev/docs/ai/skills | Correct use of the Remotion Player and timeline components |
| Diffusion Studio skills | github.com/diffusionstudio/skills | Reference for how an agent-driven editor structures editing operations |

Your organisation's skill catalog has no UI skills yet, so these are the ones to install in the builder's environment.

**Component stack:** React + TypeScript + Vite, Tailwind for styling, Radix primitives (via shadcn/ui) for accessible menus, dialogs and sliders, TanStack Query for server data, Zustand for editor state, wavesurfer.js for audio waveforms under timeline segments, and the Remotion Player for preview.

**Design direction (a starting point; the builder confirms it with the frontend-design process).** The footage is the hero, so the interface stays neutral and quiet and never tints how a shot looks. Colour carries meaning only: one colour for talking segments, one for scenic, one accent for anything the agent is doing. Pick a characterful but readable UI typeface with tabular figures so timecodes don't jitter, rather than a default system font or a separate monospace face. Motion only answers an action (a segment snapping into place, the variant tabs filling in), and reduced-motion settings are respected.

**Words in the UI** follow the user's vocabulary, not the system's: "Style" not "style profile", "Cut" not "EDL", "Talking" and "Scenic" not "A-roll" and "B-roll". Buttons say what happens ("Generate cuts", "Export video"), and the result uses the same verb ("Exported"). Errors say what went wrong and how to fix it.

**Quality floor:** light and dark themes, visible keyboard focus, WCAG AA contrast, layouts tested at 1280 and 1728 px wide. The builder takes screenshots with Playwright after each UI change and reviews them before moving on.

## One command, local first

`docker compose up` (aliased as `make up`) starts everything: the web app, the API, the workers, the databases and the local models. Then open `http://localhost:3000`. The first run builds images and downloads models; the UI shows that download with progress and time remaining like any other job.

**Services**

| Service | What it runs | Notes |
| --- | --- | --- |
| `web` | Built React app served by nginx | Port 3000, bound to 127.0.0.1 only |
| `api` | FastAPI: projects, cuts, versions, progress stream | Port 8000, bound to 127.0.0.1 only |
| `worker` | FFmpeg, PySceneDetect, whisper.cpp, OpenCV, open\_clip, the agent loop | Scale with `--scale worker=2` |
| `db` | Postgres 16 with pgvector | Projects, clips, analysis, cut versions, jobs, embeddings |
| `redis` | Redis 7 | Job queue and progress events |
| models | Docker Model Runner (agent LLM, vision model) | Runs on the Mac's GPU, outside the VM |

**The Mac GPU catch.** Containers on a Mac run inside a Linux VM that can't use the Apple GPU. Docker Model Runner solves this for the LLMs: it runs llama.cpp natively on the host with GPU acceleration, and Compose (v2.35+) can declare the models a service needs. Whisper and CLIP in the worker run on the CPU inside the container, which is slower than Apple's MLX. For speed, `make up-fast` also starts a small native sidecar (via `uv`) running mlx-whisper and CLIP on the GPU, which the worker calls at `host.docker.internal`. Pure Docker with CPU transcription is the confirmed default. To keep the 10-minute first cut on CPU, the worker transcribes only the speech regions found by voice detection and uses the largest Whisper model that fits the time budget in Phase 2 benchmarks (likely small or medium).

```yaml
services:
  web:
    build: ./web
    ports: ["127.0.0.1:3000:80"]
    depends_on: [api]
  api: &app
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports: ["127.0.0.1:8000:8000"]
    env_file: .env
    volumes:
      # media folders: one read-only mount each, from media-folders.txt (generated override)
      - ${EXPORT_DIR:-${HOME}/Movies/Rough Cuts}:/exports
      - cache:/cache
    depends_on: [db, redis]
    models: [agent_llm, vision]
  worker:
    <<: *app
    command: python -m app.worker
    ports: []
  db:
    image: pgvector/pgvector:pg16
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:7-alpine
models:
  agent_llm:
    model: ai/qwen2.5      # illustrative; pick exact 7–8B Q4 tag in Phase 0
  vision:
    model: ai/<vision-model>  # verify availability in Phase 0
volumes: { pgdata: {}, cache: {} }
```

**Files and footage.** Footage lives in several folders across the Mac, so media folders are a list, not one root. They are kept in `media-folders.txt`; `make up` generates a Compose override that mounts each one read-only at `/media/<folder name>`. In the app, Settings → Media folders lets you add or remove folders; saving updates the list and restarts the API and worker (about 10 seconds, with a progress note). The in-app picker browses only these folders, because a browser can't read local paths directly. Exports land in a separate mounted folder, also configurable. Source files are never modified.

**Local first** means no telemetry, no account, every port bound to localhost, and full offline use once models are downloaded. Nothing leaves the machine unless a cloud model is switched on.

**Prerequisites:** Docker Desktop for Apple Silicon with Model Runner enabled in Docker Desktop's settings. A `make doctor` command checks Docker version, Model Runner, free disk and memory, and prints the fix for anything missing.

## Local and cloud models

The agent talks to one `LLMClient` interface. Each role (agent, vision captions) picks its own provider, so you can, for example, keep captions local and use a cloud model only for the edit.

| Provider | When to use | Connection |
| --- | --- | --- |
| Docker Model Runner (default) | Fully local, GPU-accelerated, no extra install | OpenAI-compatible endpoint inside Compose |
| Ollama on the host | You already use Ollama models | `host.docker.internal:11434` |
| Anthropic, OpenAI, or any OpenAI-compatible API | Better edits on hard projects, faster on long footage | API key |

**Switching** happens in Settings (the default for all projects) or per run from a model menu next to Generate ("Use cloud for this run"). The agent panel always shows which model is working. Providers format tool calls differently, so the client converts them into one internal shape and the agent code never sees provider specifics.

**API keys** are entered in Settings, stored encrypted in the local database using a secret generated on first run, shown masked after saving, and never written to logs or sent back to the browser. A key can also be set in `.env` for scripted setups.

**Before a cloud run** the UI shows the estimated time and the estimated token cost, and what will be sent: text only (transcripts, shot descriptions, stats). Video and keyframes never leave the machine. If a cloud call fails mid-run, the job pauses and offers to retry or continue on the local model.

## Build phases

The job and progress system comes before any feature, so everything built afterwards reports progress from day one. Each phase ends with a check that must pass before the next starts.

### Phase 0 — Stack spike

Compose skeleton with all services, health checks, `make up` and `make doctor`. Confirm Docker Model Runner serves a 7–8B model with working tool calls and find a usable vision model (or fall back to Ollama on the host). Set up the Remotion Player (free licence, personal project), and spend half a day evaluating Diffusion Studio's code.

**Done when:** on a clean Mac, one command brings every service up green and a test prompt is answered on the GPU.

### Phase 1 — Jobs, progress and time remaining

Jobs, stages and work units in Postgres; worker progress events through Redis; server-sent events to the browser; the status pill, job drawer, pause/cancel/retry, calibration run and the estimate rules above.

**Done when:** a simulated 3-minute job shows a time remaining within ±20% from 15 seconds in, and no animated bar is visible for more than 2 seconds.

### Phase 2 — Ingest and analysis

The v1 analysis pipeline moved into workers, writing results as each clip finishes so the media bin fills in progressively. Shooting-order detection, quality flags, style profile from a reference.

**Done when:** after dropping 30 clips, the first clip card is complete within a minute, and a restart mid-analysis resumes where it stopped.

### Phase 3 — Workspace shell

Design tokens via the frontend-design process, then the four-region layout, media bin, player playing a hand-written cut, timeline, transcript view and keyboard shortcuts.

**Done when:** a 10-minute cut scrubs smoothly, screenshots in light and dark pass review, and every action works from the keyboard.

### Phase 4 — Agent and variants

The agent loop from v1 behind `LLMClient`, outline first, filling the timeline section by section, producing three variants, with its plan and activity streaming to the agent panel.

**Done when:** for 30 minutes of footage on the M3 Pro, the first variant is watchable within 10 minutes of dropping the footage, analysis included, and all three variants pass the validator.

### Phase 5 — Refinement

Ask-the-agent changes, transcript strike-through editing, remove/lock/nudge on the timeline, versions with undo, redo and compare. All edits go through the validator.

**Done when:** a change request regenerates only the affected sections, locked segments survive, and any version can be restored.

### Phase 6 — Export

Background FFmpeg render with exact progress, MP4 plus timeline file (FCPXML/OTIO), notification and "Show in folder".

**Done when:** a 10-minute export has frame-accurate cuts, no clicks, stays in sync and opens in DaVinci Resolve.

### Phase 7 — Cloud models and settings

Provider settings per role, encrypted key storage, per-run model menu, cost and data preview before cloud runs, fall back to local on failure.

**Done when:** the same project runs end to end on local and on a cloud model by changing one setting, and no key appears in any log.

### Phase 8 — Hardening and evaluation

Test sets with automatic scores (pacing vs. reference, dead air, rejected shots, duplicates, runtime error, time-to-first-cut), the optional native fast mode, very long files, variable frame rate phone footage, missing audio.

**Done when:** all test sets pass and scores are tracked so regressions show up.

## Decisions

- Personal project: Remotion's free licence applies.
- CPU-only transcription in Docker is the default; the native fast mode stays optional.
- Footage lives in several folders, so media folders are a configurable list.
- Time to first cut for 30 minutes of footage: 10 minutes or less, analysis included.
