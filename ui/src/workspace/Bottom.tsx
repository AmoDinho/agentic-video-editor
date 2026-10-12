import { transcript } from "./fixtures";
import { useEditor } from "../store";

const blocks = ["t", "s", "t", "s", "s", "t", "s", "t", "e", "a", ...Array(18).fill("g")];

export function Bottom() {
  const screen = useEditor((state) => state.screen);
  const tab = useEditor((state) => state.bottomTab);
  const setBottomTab = useEditor((state) => state.setBottomTab);
  const setScreen = useEditor((state) => state.setScreen);
  const struck = useEditor((state) => state.struck);
  const toggleStrike = useEditor((state) => state.toggleStrike);

  const tabs =
    screen === "compare"
      ? (["compare", "timeline", "transcript"] as const)
      : screen === "analyse"
        ? (["footage", "timeline", "transcript"] as const)
        : (["timeline", "transcript"] as const);

  return (
    <section className="flex h-[27%] min-h-[160px] flex-col border-t border-line">
      <div className="flex gap-4 px-4 text-sm">
        {tabs.map((item) => (
          <button
            key={item}
            type="button"
            className={`py-2 capitalize ${tab === item ? "border-b border-ink" : "text-muted"}`}
            onClick={() => {
              setBottomTab(item);
              if (item === "transcript" && (screen === "refine" || screen === "transcript")) setScreen("transcript");
              if (item === "timeline" && screen === "transcript") setScreen("refine");
            }}
          >
            {item === "compare" ? "Compare timelines" : item === "footage" ? "Footage" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-4 pb-2">
        {screen === "empty" ? <p className="grid h-full place-items-center rounded-md bg-raised text-sm text-muted">Your cut will appear here, section by section</p> : null}
        {screen === "analyse" && tab === "footage" ? <FootageStrip /> : null}
        {screen === "compare" && tab === "compare" ? <CompareRows /> : null}
        {screen === "generate" ? <p className="text-sm text-muted">Section 3 of 5 is still being selected. Finished sections are already on the timeline.</p> : null}
        {(screen === "refine" || screen === "generate") && tab !== "transcript" ? <CutStrip working={screen === "generate"} /> : null}
        {tab === "transcript" || screen === "transcript" ? (
          <Transcript struck={struck} onStrike={toggleStrike} />
        ) : null}
      </div>
    </section>
  );
}

function CutStrip({ working }: { working: boolean }) {
  const select = useEditor((state) => state.select);
  const selectedId = useEditor((state) => state.selectedId);
  const parts = ["t", "s", "t", "s", "s", "t", "t", "s", "t", "s", "t", "s"];
  return (
    <div className="mt-3 flex h-10 gap-0.5">
      {parts.map((kind, index) => (
        <button
          key={index}
          type="button"
          aria-label={kind === "t" ? "Talking" : "Scenic"}
          className={`h-full flex-1 ${kind === "t" ? "bg-talking" : "bg-scenic"} ${selectedId && index === 7 ? "outline outline-1 outline-paper" : ""} ${working && index > 7 ? "opacity-30" : ""}`}
          onClick={() => select("IMG_2047.MOV")}
        />
      ))}
    </div>
  );
}

function FootageStrip() {
  return (
    <div>
      <p className="text-xs text-muted">All footage in shooting order</p>
      <div className="mt-2 flex h-8 gap-0.5">
        {blocks.map((kind, index) => (
          <span
            key={index}
            className={`h-full flex-1 rounded-sm ${
              kind === "t" ? "bg-talking" : kind === "s" ? "bg-scenic" : kind === "e" ? "bg-danger" : kind === "a" ? "bg-agent" : "bg-raised"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

function CompareRows() {
  return (
    <div className="space-y-2 text-xs">
      {["Tight", "Matched", "Relaxed"].map((name) => (
        <div key={name} className="flex items-center gap-3">
          <span className="w-16">{name}</span>
          <div className={`flex h-6 flex-1 gap-0.5 ${name === "Matched" ? "outline outline-1 outline-paper" : ""}`}>
            {Array.from({ length: name === "tight" ? 8 : 12 }, (_, index) => (
              <span key={index} className={`h-full flex-1 ${index % 2 ? "bg-talking" : "bg-scenic"}`} />
            ))}
          </div>
        </div>
      ))}
      <p className="text-muted">Bars are sections in shooting order. Gaps line up where a variant drops a section.</p>
    </div>
  );
}

function Transcript({ struck, onStrike }: { struck: number[]; onStrike: (index: number) => void }) {
  return (
    <div className="space-y-2 text-sm">
      {transcript.map((row) => (
        <p key={row.t}>
          <span className="mr-3 text-muted">{row.t}</span>
          {row.scenic ? <span className="text-scenic">{row.scenic} </span> : null}
          {row.source ? <span className="mr-2 rounded bg-talking/20 px-1 text-talking">{row.source}</span> : null}
          {row.text}
          {row.words?.map((word, index) => {
            const gone = row.struck?.includes(index) || struck.includes(index);
            return (
              <button
                key={`${row.t}-${word}-${index}`}
                type="button"
                className={`mr-1 ${gone ? "text-muted line-through" : ""}`}
                onClick={() => onStrike(index)}
              >
                {word}
              </button>
            );
          })}
        </p>
      ))}
      <p className="text-xs text-muted">Struck words are removed from the cut. Select words and press Delete to strike them.</p>
    </div>
  );
}
