# Token plan

Checked against the spec and the design PNGs before any component was built.

## What the brief requires

The footage is the hero. Chrome stays neutral and never tints a shot. Colour means something: Talking, Scenic, or the agent. Timecodes use tabular figures. Motion answers an action and respects reduced motion. Words are Style, Cut, Talking, Scenic, Generate cuts, Export video.

## What the PNGs actually use

Sampled from the empty-project and analysing frames, which are 2× exports of a 1440×900 window.

- Page `#16171a`, well `#0f1012`, raised chip `#1f2124`, hairline `#2a2c30`
- Primary action `#eceae5` on `#0f1012`. Top-bar Export is quieter, `#6c6b6b`
- Talking `#7eb2ff`. Scenic `#f2b868`. Agent `#60d8b8` on `#15332d`
- Error `#f78e7b`
- Left column about 19%, right about 23%, bottom about 27%

## Decisions

- One family, IBM Plex Sans, with `font-variant-numeric: tabular-nums`. No second monospace face. The PNGs do not name a face; Plex is already the project face and has tabular figures.
- Dark is the designed theme. Light inverts the neutrals and keeps the three meaning colours, darkened enough for AA on white.
- No indeterminate bar. A job with no rate says "Estimating time…" next to the step count.
- Press feedback is `scale(0.97)` in 140ms ease-out. Overlays enter from `scale(0.98)` and opacity, not from nothing. Keyboard actions do not animate.
- Hover styles are gated to fine pointers. Reduced motion drops transforms and keeps opacity.
