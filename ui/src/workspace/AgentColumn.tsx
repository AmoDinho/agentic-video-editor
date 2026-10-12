import { useEditor } from "../store";

export function AgentColumn() {
  const screen = useEditor((state) => state.screen);
  const setOverlay = useEditor((state) => state.setOverlay);
  return (
    <aside className="flex w-[23%] min-w-[240px] flex-col border-l border-line text-sm">
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <span>Agent</span>
        <span className="text-muted">Local · Qwen 2.5 7B</span>
      </header>
      <div className="flex-1 overflow-auto px-4 py-4">
        {screen === "empty" ? <EmptyAgent /> : null}
        {screen === "analyse" ? <AnalyseAgent /> : null}
        {screen === "generate" ? <GenerateAgent /> : null}
        {screen === "compare" ? <CompareAgent onJobs={() => setOverlay("jobs")} /> : null}
        {screen === "refine" || screen === "transcript" ? <RefineAgent screen={screen} /> : null}
      </div>
      <form className="border-t border-line p-3" onSubmit={(event) => event.preventDefault()}>
        <div className="flex gap-2">
          <input className="w-full rounded-md border border-line bg-well px-3 py-2" placeholder="Ask for a change" aria-label="Ask for a change" />
          {screen !== "empty" && screen !== "analyse" ? (
            <button type="submit" className="press rounded-md bg-paper px-3 text-page">
              Send
            </button>
          ) : null}
        </div>
      </form>
    </aside>
  );
}

function EmptyAgent() {
  const steps = [
    ["Drop footage.", "Each clip is analysed in shooting order."],
    ["Choose a style.", "A reference video or a saved style."],
    ["Generate cuts.", "Three variants: tight, matched, relaxed."],
    ["Refine and export.", "Ask, edit the transcript, or trim the timeline."],
  ];
  return (
    <>
      <p>The agent starts as soon as you choose a style. Here is what happens:</p>
      <ol className="mt-4 space-y-3">
        {steps.map(([title, body], index) => (
          <li key={title} className="flex gap-3">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-raised text-muted">{index + 1}</span>
            <span>
              <span className="font-medium">{title}</span> <span className="text-muted">{body}</span>
            </span>
          </li>
        ))}
      </ol>
    </>
  );
}

function AnalyseAgent() {
  return (
    <>
      <p className="inline-block rounded-full bg-raised px-2 py-0.5 text-xs text-muted">Waiting for you to generate</p>
      <p className="mt-4">When you press Generate, I will:</p>
      <ul className="mt-3 space-y-2 text-muted">
        <li>Outline the trip into sections, in shooting order</li>
        <li>Pick and trim shots for each section to match the style</li>
        <li>Check each section, then build tight and relaxed variants</li>
      </ul>
      <div className="mt-4 rounded-lg bg-raised p-3">
        <p className="font-medium">Footage so far</p>
        <p className="mt-1 text-muted">9 clips ready · 11:20 talking · 6:05 scenic · 1 clip needs attention</p>
      </div>
    </>
  );
}

function GenerateAgent() {
  const plan = ["Outline: 5 sections from shooting order", "1 · Drive in", "2 · Beach camp", "3 · Morning hike", "4 · Village and market", "5 · Last campfire", "Build Tight and Relaxed"];
  return (
    <>
      <p className="text-agent">About 4 min left</p>
      <p className="text-muted">Step 7 of 15 · Section 3 of 5 · Revision 0 of up to 4</p>
      <ol className="mt-4 space-y-2">
        {plan.map((item, index) => (
          <li key={item} className={index === 3 ? "text-agent" : index < 3 ? "text-ink" : "text-muted"}>
            {index < 3 ? "✓ " : index === 3 ? "● " : "○ "}
            {item}
          </li>
        ))}
      </ol>
      <p className="mt-4 text-xs tracking-wide text-muted">NOW</p>
      <p className="mt-1">Choosing 3 of 6 hike shots: keeping the steadiest wide shots and the ridge view.</p>
    </>
  );
}

function CompareAgent({ onJobs }: { onJobs: () => void }) {
  return (
    <>
      <div className="rounded-lg bg-raised p-3">
        <p className="font-medium">Three cuts are ready. All passed the check.</p>
        <p className="mt-1 text-muted">Matched is closest to your reference. Tight drops most of the market section; Relaxed keeps the long campfire conversation.</p>
      </div>
      <p className="mt-4 text-xs tracking-wide text-muted">WHAT I LEFT OUT</p>
      <ul className="mt-2 list-disc space-y-1 pl-4 text-muted">
        <li>GOPR0193 couldn't be read (unsupported codec)</li>
        <li>4 shaky handheld shots on the hike</li>
        <li>2 near-duplicate sunset shots</li>
      </ul>
      <button type="button" className="mt-3 text-talking" onClick={onJobs}>
        See the full run in the job drawer
      </button>
    </>
  );
}

function RefineAgent({ screen }: { screen: "refine" | "transcript" }) {
  return (
    <>
      {screen === "transcript" ? (
        <div className="rounded-lg bg-raised p-3">
          <p className="text-agent">v8 · your transcript edit</p>
          <p className="mt-1">Removed 9 words from the beach camp chat. The cut is 4.2 s shorter.</p>
          <p className="mt-1 text-muted">Each cut snapped to the nearest pause so no word is clipped mid-sound.</p>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {["Tighten the market section", "End on the fire, not the stars", "Less of me talking"].map((chip) => (
            <span key={chip} className="rounded-full bg-raised px-2 py-1 text-xs">
              {chip}
            </span>
          ))}
        </div>
      )}
    </>
  );
}
