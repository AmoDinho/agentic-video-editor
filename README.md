# Agentic Video Editor

A local-first editor that turns a folder of footage into a rough cut that follows a reference video. One command starts the stack:

```
make up
```

Then open http://127.0.0.1:3000.

`make doctor` checks Docker, Compose, Model Runner, free disk, and memory, and prints the fix for anything missing. Footage folders go in `media-folders.txt`, one path per line. They are mounted read-only. Source files are never modified.

The product spec is `docs/Agentic Video Editor — UI-First Spec v2.md`. The v1 analysis pipeline, cut contract, and validator stay. Licence notes for Remotion and Diffusion Studio are in `docs/licences.md`.
