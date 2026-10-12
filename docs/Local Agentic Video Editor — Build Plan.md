# Local Agentic Video Editor — Build Plan

Oct 6, 2026 · @Amogelang

## Overview

Build a desktop-local tool that takes one reference video plus a folder of raw clips, and autonomously produces a stitched rough cut that edits like the reference, exported as an MP4. Everything runs on the user's machine: analysis models, the agent's LLM, and rendering.

**In scope for v1:** reviewing every source file, choosing segments, trimming, ordering, and concatenating them into one continuous cut with the original audio intact. Matching the reference's pacing (shot lengths, cut rhythm, total runtime, how much is talking vs. visuals).

**Out of scope for v1:** transitions, animations, motion graphics, titles, sound effects, music beds, colour grading, and captions. The output is a rough cut to watch, not a finished video.

**Assumptions:** sources are common formats (MP4/MOV, H.264/H.265/ProRes) with mixed resolutions and frame rates; the reference is used for *style* (pacing and structure), not copied content; footage mixes talking-to-camera with scenic shots carrying natural sound, each kept with its own audio; sentences are never cut mid-word; and segments always play in the order they were shot. A tiny 10–20 ms audio fade at each cut is allowed to prevent clicks, since it is inaudible and not a creative transition.

## How it works

Both inputs go through the same analysis pipeline: the reference becomes a style profile, the clips become a searchable index. The agent reads both and writes an edit decision list; only a list that passes the validator reaches FFmpeg.

&#91;embedded content: one editing run · inputs to export\]

The agent checks stats from its own fast preview and revises up to four times before the final export.

## Local tech stack

Python 3.11+ for the whole backend, FFmpeg for every read and write of media, and Ollama for local models. All model choices below are swappable behind small interfaces.

| Job | Recommended (local) | Notes |
| --- | --- | --- |
| Probe, cut, normalise, render | FFmpeg + ffprobe | Only component that touches pixels. Called via subprocess, never by the LLM directly. |
| Shot / scene detection | PySceneDetect (ContentDetector + AdaptiveDetector) | Gives shot boundaries for both reference and sources. |
| Speech-to-text with word timestamps | mlx-whisper (large-v3-turbo), Apple Silicon native | Word timings let the agent cut on sentence boundaries. |
| Voice activity / silence | Silero VAD | Finds dead air and speech regions. |
| Loudness | FFmpeg ebur128 filter | Per-segment loudness; final loudnorm to −14 LUFS. |
| Shot quality | OpenCV (Laplacian blur, frame-diff motion, exposure) | Rejects blurry, shaky, black or overexposed frames. |
| Visual description of shots | Qwen2.5-VL 3B or Moondream via Ollama | Captions 1–3 keyframes per shot so the agent can "see". |
| Visual similarity search | open\_clip (ViT-B/32) embeddings | Lets the agent search "wide shot of the street" across all clips. |
| Agent brain | Qwen2.5 7B or Llama 3.1 8B instruct (4-bit) via Ollama, or a cloud model via API key | Chosen in config; see LLM providers. |
| Metadata store | SQLite + JSON files per asset | Caches all analysis so re-runs are fast. |
| Interchange export | OpenTimelineIO | Exports the cut to Premiere / Resolve / FCP for finishing. |
| UI | CLI (Typer) for testing; FastAPI + React (Vite) web UI on localhost |  |

**Target hardware: MacBook Pro M3 Pro, 18 GB unified memory.** That fits one mid-size model at a time, so stages load models one after another and unload each when done (Ollama `keep_alive: 0`). Use a 7–8B agent model at 4-bit (about 5 GB), a 3B vision model, mlx-whisper for transcription, and PyTorch on MPS for CLIP; a 14B agent model only fits with nothing else loaded. Previews encode with the hardware encoder (`h264_videotoolbox`); final exports use libx264 for quality. Benchmark analysis speed in Phase 1 and record it.

## The edit decision list (EDL)

The agent never renders video. It outputs a JSON edit decision list; a deterministic validator checks it and FFmpeg renders it. This keeps the LLM's mistakes cheap and the output reproducible.

```json
{
  "version": 1,
  "project_id": "trip-vlog-01",
  "output": { "width": 1920, "height": 1080, "fps": 30, "audio_rate": 48000 },
  "target_duration_s": 480,
  "segments": [
    {
      "id": "seg_001",
      "source": "clips/IMG_0412.MOV",
      "in_s": 12.40,
      "out_s": 16.10,
      "audio": "source",
      "role": "a_roll",
      "reason": "Opening line, clean audio, matches reference cold-open length"
    }
  ],
  "notes": "Agent's summary of the structure it chose"
}
```

The validator rejects: missing files, `in_s`/`out_s` outside the clip, segments under 0.3 s, cuts landing inside a spoken word, the same source range used twice, totals more than ±10% off target, and segments out of shooting order. `role` is `a_roll` (speech carries the story) or `b_roll` (visuals); `reason` is required so the user can see why each cut was made.

## Build phases

Eight phases, each ending in something runnable. Phases 1 and 2 can be built in parallel; everything else is sequential. Do not start a phase until the previous one's acceptance check passes.

### Phase 0 — Foundations

Set up the repo, a `editor` CLI, config file, hardware detection, an FFmpeg presence check, the SQLite schema, and the EDL schema with its validator. Write a minimal renderer that takes a hand-written EDL and concatenates segments.

**Done when:** `editor render sample_edl.json` produces a playable MP4 from three test clips with different frame rates and resolutions, with no audio drift.

### Phase 1 — Source ingestion and analysis

For each source file: probe metadata, generate a 540p proxy, detect shots, transcribe with word timestamps, run VAD, measure loudness per shot, score blur/motion/exposure, caption 1–3 keyframes per shot with the vision model, compute CLIP embeddings, and record when each clip was shot (QuickTime creation date via ffprobe, falling back to file modified time, then filename). Cache everything keyed by file hash so unchanged files are never re-analysed.

**Done when:** `editor analyze ./clips` writes one analysis JSON per file and a re-run on the same folder finishes in seconds.

### Phase 2 — Reference analysis (style profile)

Run the same analysis on the reference, then derive a `style_profile.json`: total runtime, cuts per minute, shot-length distribution (median, p10, p90), share of runtime with speech, whether cuts tend to land on sentence ends or mid-flow, typical length of A-roll stretches between B-roll inserts, and a coarse structure (opening, body, closing) with durations. Also store a plain-English summary the agent can read.

**Done when:** profiles from two very different references (fast vlog vs. slow documentary) are clearly different and the numbers match a manual spot check.

### Phase 3 — Heuristic baseline editor (no LLM)

A deterministic assembler: rank shots by quality, drop rejects, keep speech regions whole, trim B-roll to lengths sampled from the reference's distribution, order chronologically by source timestamp, and stop at target runtime. This is the fallback and the benchmark the agent must beat.

**Done when:** it produces a watchable rough cut with no blurry shots, no dead air over 1.5 s, and pacing within 15% of the reference.

### Phase 4 — Agent layer

Wire a local LLM with tool calling to the analysis data (tools are listed in the agent design section). The agent plans a structure, picks and trims segments, emits an EDL, validates it, inspects stats, and revises. Hard cap on iterations and tokens.

**Done when:** given a reference and 20+ clips, the agent produces a valid EDL end to end with no human input, and in blind viewing it is preferred over the Phase 3 baseline on most test sets.

### Phase 5 — Rendering and export

Two render modes. Preview: from proxies, 540p, fast, for the agent's self-review and the user. Final: from originals, normalised to the EDL's resolution and fps (scale + pad, constant frame rate), H.264/AAC MP4, 10–20 ms audio fades at each cut, loudnorm to −14 LUFS. Also export the timeline via OpenTimelineIO (FCPXML / EDL) so the cut opens in Premiere or Resolve.

**Done when:** a 10-minute final export has frame-accurate cuts, no audio clicks, stays in sync end to end, and opens correctly in DaVinci Resolve.

### Phase 6 — Local UI

Build the screens in the User interface section, in this order: Settings and New project, Run, Review, Export, then Projects and Media bin. Start the Run screen as soon as Phase 3 works, so agent runs can be watched while Phase 4 is built. Locked segments and agent notes from the Review screen need matching support in the agent's tools.

**Done when:** a non-technical user can go from folder to exported MP4 without the terminal; can remove, lock and nudge segments, then regenerate with a note and see locked segments kept; and can scrub a 10-minute preview without stutter.

### Phase 7 — Evaluation and hardening

Build 5–10 test sets (reference + clips). Score each run automatically: pacing distance to the reference, dead-air seconds, rejected-shot count, duplicate footage, runtime error, and render time. Add handling for long files (2 h+), variable frame rate phone footage, missing audio tracks, and corrupt files.

**Done when:** all test sets render without errors and the metrics are tracked across changes so regressions are caught.

## Agent design

The agent works from text summaries of the footage, not raw video, so a mid-size local model can handle hours of clips. It edits in a plan → assemble → check → revise loop and stops after 4 revisions or when checks pass.

**Tools the agent can call**

| Tool | Returns |
| --- | --- |
| `get_style_profile()` | Reference pacing numbers and plain-English summary |
| `list_clips()` | Every source with duration, shot count, speech share, quality summary |
| `get_clip_detail(clip_id)` | Shots with timestamps, captions, quality scores, transcript |
| `search_shots(query, k)` | Top shots by CLIP + caption similarity to a text query |
| `get_transcript(clip_id, start, end)` | Words with timestamps for that range |
| `snap_to_boundary(clip_id, time)` | Nearest safe cut point (sentence end, silence, or shot change) |
| `submit_edl(edl)` | Validator result: pass, or a list of specific errors |
| `evaluate_edl(edl)` | Pacing distance to reference, runtime, dead air, duplicates, coverage of sources |

**Loop**

1. Read the style profile and the user's brief; write a short outline (sections with target durations).
2. Survey all clips; identify the A-roll (speech that carries the story) and candidate B-roll.
3. Walk the clips in shooting order: keep the best talking stretches whole, and trim the scenic shots between them to the reference's shot-length rhythm, natural sound included.
4. Snap every cut to a safe boundary, then `submit_edl`.
5. Run `evaluate_edl`; if pacing or runtime is off, revise the weakest sections and resubmit.
6. Render a preview and write a one-paragraph summary of the cut for the user.

**Guardrails:** the validator, not the LLM, enforces timing rules; context is kept small by paging clip details on demand; every run logs all tool calls to a JSON trace so bad edits can be debugged; source files are opened read-only and never modified.

## LLM providers

The agent talks to one `LLMClient` interface with two backends: local (Ollama) and cloud (any provider with tool calling, via API key). Switching is a config change, not a code change.

```yaml
llm:
  provider: ollama          # ollama | anthropic | openai | openai_compatible
  model: qwen2.5:7b-instruct
  base_url: http://localhost:11434
  api_key_env: null         # e.g. ANTHROPIC_API_KEY when provider is cloud
  max_iterations: 4
  max_tokens_per_run: 200000
```

API keys come from an environment variable or the macOS Keychain, are set from the UI's settings screen, and are never written to the repo, config file or run logs. Providers format tool calls differently, so the client normalises them into one internal shape and agent code never sees provider specifics. In cloud mode only text leaves the machine (transcripts, shot captions, stats); video and keyframes stay local, and the UI shows which mode is active before each run.

## User interface

The UI is a local web app: a FastAPI backend plus a React (Vite) single page on `localhost`, opened in the browser. The CLI stays for testing and scripting. Wrapping it as a native Mac app with Tauri is a later option, not v1.

**Screens**

| Screen | What the user does | What it shows |
| --- | --- | --- |
| Projects | Open or create a project | Recent projects with clip count, runtime, last export |
| New project | Pick the clips folder and reference video, set target length, write an optional brief | Folder browser served by the backend, since a browser page can't read local paths |
| Media bin | Include or exclude clips before a run | Thumbnails in shooting order, date shot, duration, analysis status, quality flags |
| Run | Start, watch, cancel | Progress per stage (analysis per file, then each agent iteration) and a readable agent log |
| Review | Watch the cut and steer it | Preview player, segment strip, side-by-side stats vs. reference |
| Export | Choose preset and destination, export | Resolution and fps preset, output path, progress, "Show in Finder" |
| Settings | Choose LLM provider and model, enter API key, manage cache | Ollama model status, Keychain-stored key (masked), cache size with a clear button |

**Review screen (the core of the UI).** A player for the 540p preview sits above a horizontal strip of segments in play order, coloured by type (talking vs. scenic) and sized by duration. Clicking a segment jumps the player there and opens a side panel with the source file, in/out times, and the agent's `reason`. From that panel the user can remove a segment, lock it, or nudge its in/out points by snapped steps. A text box sends a note to the agent ("shorter overall", "more scenery in the middle") and regenerates; locked segments survive regeneration. A stats row compares runtime, cuts per minute and median shot length with the reference.

**How the UI talks to the backend**

| Endpoint | Purpose |
| --- | --- |
| `POST /projects` | Create a project from folder, reference, target length, brief |
| `POST /projects/{id}/analyze` | Run or resume analysis |
| `POST /projects/{id}/edit` | Run the agent, optionally with a note and locked segment ids |
| `GET /projects/{id}/edl` · `PATCH …/edl` | Read the cut; apply manual remove/lock/nudge (validated server-side) |
| `GET /projects/{id}/events` | Server-sent events for progress and agent log |
| `GET /media/{id}/proxy` | Proxy video with HTTP range support for scrubbing |
| `POST /projects/{id}/export` | Final render and timeline export |
| `GET /settings` · `PUT /settings` | Provider, model, API key (stored in Keychain), cache |

Every manual change goes through the same validator as the agent's edits. Long jobs run in a background worker, so closing the browser tab does not stop a render.

**Out of scope for the UI in v1:** a full multi-track timeline, drag-to-reorder (order is fixed by shooting time), effects or titles, and multi-user access.

## Handoff notes for the builder agent

Build phase by phase and demo each acceptance check before moving on. Prefer boring, well-maintained libraries; keep each pipeline stage a separate module with JSON in and JSON out so stages can be tested and swapped alone.

- Never let the LLM produce FFmpeg commands; it only produces EDLs.
- Cache all analysis by file hash; never re-run an expensive step on unchanged input.
- Use frame-accurate re-encoding for final cuts (no stream-copy cuts on non-keyframes).
- Convert variable frame rate footage to constant frame rate before analysis to avoid sync drift.
- Ship sample test media (short, royalty-free) in the repo for Phase 0–5 checks.

**Decisions confirmed by the owner**

- Footage: a mix of talking-to-camera and scenic shots with natural sound; both keep their own audio.
- Hardware: MacBook Pro M3 Pro with 18 GB unified memory.
- Order: the cut always follows the order clips were shot; the agent chooses what to keep and how long, never the sequence.
- LLM: local by default, switchable to a cloud model with an API key.
