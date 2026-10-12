import { styles, variants } from "./fixtures";
import { useEditor } from "../store";

export function Centre() {
  const screen = useEditor((state) => state.screen);
  if (screen === "empty") return <Drop />;
  if (screen === "analyse") return <ChooseStyle />;
  if (screen === "generate") return <Generating />;
  if (screen === "compare") return <Compare />;
  return <PlayerStub />;
}

function Drop() {
  return (
    <div className="m-6 grid flex-1 place-items-center rounded-xl border border-dashed border-line text-center">
      <div>
        <h1 className="text-xl">Drop a folder of clips to start</h1>
        <p className="mt-2 max-w-md text-sm text-muted">Analysis starts the moment clips arrive. Your source files are never changed.</p>
        <p className="mt-6 text-xs tracking-wide text-muted">OR PICK FROM YOUR MEDIA FOLDERS</p>
      </div>
    </div>
  );
}

function ChooseStyle() {
  const setScreen = useEditor((state) => state.setScreen);
  const setOverlay = useEditor((state) => state.setOverlay);
  return (
    <div className="flex-1 overflow-auto px-6 py-5">
      <h1 className="text-2xl">Choose a style</h1>
      <p className="mt-1 text-sm text-muted">You can generate now. The agent works front to back and waits only for clips it still needs.</p>
      <div className="mt-4 grid grid-cols-[1.4fr_1fr] gap-4">
        <article className="rounded-xl p-4 outline outline-1 outline-paper">
          <div className="flex justify-between text-xs tracking-wide text-muted">
            <span>REFERENCE VIDEO</span>
            <span className="rounded-full bg-raised px-2 py-0.5">Selected</span>
          </div>
          <p className="mt-3 font-medium">coast-vlog-reference.mp4</p>
          <p className="text-sm text-muted">8:12 · analysed just now</p>
          <p className="mt-3 font-medium">About 9 cuts a minute, most shots 2–5 s, 60% talking, around 8 minutes.</p>
          <div className="mt-3 flex h-1.5 overflow-hidden rounded-full">
            <span className="w-[60%] bg-talking" />
            <span className="w-[40%] bg-scenic" />
          </div>
        </article>
        <div>
          <p className="text-xs tracking-wide text-muted">SAVED STYLES</p>
          <ul className="mt-2 space-y-2">
            {styles.map((style) => (
              <li key={style.name} className="rounded-lg bg-raised px-3 py-2">
                <p className="font-medium">{style.name}</p>
                <p className="text-sm text-muted">{style.line}</p>
              </li>
            ))}
          </ul>
          <button type="button" className="mt-2 text-sm text-talking">
            + Use another reference video
          </button>
        </div>
      </div>
      <div className="mt-5">
        <p>
          Brief <span className="text-muted">Optional</span>
        </p>
        <div className="mt-2 grid grid-cols-[1fr_8rem] gap-3">
          <label className="text-sm text-muted">
            Direction
            <input className="mt-1 w-full rounded-md border border-line bg-well px-3 py-2 text-ink" defaultValue="Warm and unhurried. Open on the drive in, end at the last campfire." />
          </label>
          <label className="text-sm text-muted">
            Target length
            <input className="mt-1 w-full rounded-md border border-line bg-well px-3 py-2 text-ink" defaultValue="8 min" />
          </label>
        </div>
        <p className="mt-2 text-sm text-muted">Target length comes from the style. Change it if you need a different runtime.</p>
      </div>
      <div className="mt-5 flex items-center gap-3">
        <button type="button" className="press rounded-md bg-paper px-4 py-2 text-sm text-page" onClick={() => setScreen("generate")}>
          Generate cuts
        </button>
        <button type="button" className="press rounded-md bg-raised px-3 py-2 text-sm" onClick={() => setOverlay("cloud")}>
          <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-agent" />
          Local · Qwen 2.5 7B
        </button>
        <span className="text-sm text-muted">Three variants · first one watchable in about 8 min</span>
      </div>
    </div>
  );
}

function Generating() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex gap-2 px-4 pt-3 text-sm">
        <span className="rounded-full px-3 py-1 outline outline-1 outline-paper">Matched · 3:12 so far</span>
        <span className="rounded-full px-3 py-1 text-muted">Tight · after Matched</span>
        <span className="rounded-full px-3 py-1 text-muted">Relaxed · after Matched</span>
      </div>
      <div className="m-4 grid flex-1 place-items-center rounded-lg bg-[#1c2428] text-center">
        <div>
          <p className="text-sm">Section 2 · Beach camp</p>
          <p className="mt-4 max-w-sm text-sm text-muted">Watch the first two sections while the agent builds the rest. The player stops where the cut ends for now.</p>
          <p className="mt-4 text-sm">01:54 / 03:12 ready of about 8:00</p>
        </div>
      </div>
    </div>
  );
}

function Compare() {
  const setScreen = useEditor((state) => state.setScreen);
  const setVariant = useEditor((state) => state.setVariant);
  return (
    <div className="flex-1 overflow-auto px-5 py-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl">Pick a cut to refine</h1>
          <p className="text-sm text-muted">Same footage, same order. Hover a strip to scrub, click to play.</p>
        </div>
        <p className="text-sm text-muted">Style: about 9 cuts a minute · 2–5 s shots · 60% talking · 8 min</p>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3">
        {variants.map((cut) => (
          <article key={cut.id} className={`rounded-xl bg-raised/40 p-3 ${cut.closest ? "outline outline-1 outline-paper" : ""}`}>
            <div className={`grid h-28 place-items-center rounded-md ${cut.id === "tight" ? "bg-[#5c4a3a]" : cut.id === "matched" ? "bg-[#3d4c52]" : "bg-[#5d6848]"}`}>
              <span className="rounded-full bg-paper px-2 py-1 text-xs text-page">{cut.chip}</span>
            </div>
            <div className="mt-2 flex h-3 gap-0.5">
              {Array.from({ length: 12 }, (_, index) => (
                <span key={index} className={`h-full flex-1 rounded-sm ${index % 2 ? "bg-talking" : "bg-scenic"}`} />
              ))}
            </div>
            <h2 className="mt-3 text-lg">
              {cut.title} {cut.runtime}
            </h2>
            {cut.closest ? <p className="text-xs text-agent">Closest to the style</p> : null}
            <p className="mt-1 text-sm text-muted">{cut.blurb}</p>
            <dl className="mt-3 grid grid-cols-2 gap-y-1 text-sm">
              <dt className="text-muted">Cuts</dt>
              <dd>{cut.cuts}</dd>
              <dt className="text-muted">Pace</dt>
              <dd>{cut.pace}</dd>
              <dt className="text-muted">Most shots</dt>
              <dd>{cut.shots}</dd>
              <dt className="text-muted">Talking</dt>
              <dd>{cut.talking}</dd>
            </dl>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                className={`press flex-1 rounded-md px-3 py-2 text-sm ${cut.closest ? "bg-paper text-page" : "bg-raised"}`}
                onClick={() => {
                  setVariant(cut.id);
                  setScreen("refine");
                }}
              >
                Pick this cut
              </button>
              <button type="button" className="press rounded-md bg-raised px-3 py-2 text-sm">
                Play
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function PlayerStub() {
  const screen = useEditor((state) => state.screen);
  const variant = useEditor((state) => state.variant);
  const setScreen = useEditor((state) => state.setScreen);
  const runtime = screen === "transcript" ? "07:43" : "07:52";
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex gap-2 px-4 pt-3 text-sm">
        {variants.map((cut) => (
          <button
            key={cut.id}
            type="button"
            className={`rounded-full px-3 py-1 ${variant === cut.id ? "outline outline-1 outline-paper" : "text-muted"}`}
            onClick={() => setScreen("refine")}
          >
            {cut.title} {variant === cut.id ? runtime : cut.runtime}
          </button>
        ))}
      </div>
      <div className="m-4 grid flex-1 place-items-end rounded-lg bg-[#3a322c] p-4 text-center">
        {screen === "transcript" ? <p className="mx-auto mb-6 rounded-full bg-black/40 px-3 py-1 text-sm">we got here just as the light was going</p> : null}
      </div>
      <p className="px-4 pb-2 text-sm">
        {screen === "transcript" ? "01:12 / 07:43" : "00:24 / 07:52"}
        <span className="ml-3 text-muted">Plays straight from the cut. No render needed.</span>
      </p>
    </div>
  );
}
