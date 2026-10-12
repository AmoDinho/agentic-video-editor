import { clock, roleLabel, useEditor, type Segment } from "../store";
import { sampleWords } from "./sample";

export function Timeline({ segments }: { segments: Segment[] }) {
  const { bottomTab, setBottomTab, selectedId, select, playhead, setPlayhead } = useEditor();
  const total = segments.reduce((sum, segment) => sum + (segment.out_s - segment.in_s), 0) || 1;
  const selected = segments.find((segment) => segment.id === selectedId);
  return (
    <section className="flex h-[27%] min-h-[180px] border-t border-line">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex gap-4 px-4 text-sm">
          {(["timeline", "transcript", "footage"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              className={`py-2 capitalize ${bottomTab === tab ? "border-b border-ink" : "text-muted"}`}
              onClick={() => setBottomTab(tab)}
            >
              {tab === "timeline" ? "Timeline" : tab === "transcript" ? "Transcript" : "Footage"}
            </button>
          ))}
        </div>
        {segments.length === 0 ? (
          <div className="m-3 grid flex-1 place-items-center rounded-md bg-raised text-sm text-muted">
            Your cut will appear here, section by section
          </div>
        ) : bottomTab === "transcript" ? (
          <Transcript />
        ) : (
          <div className="relative m-3 flex flex-1 overflow-hidden rounded-md bg-well">
            {segments.map((segment) => {
              const width = ((segment.out_s - segment.in_s) / total) * 100;
              return (
                <button
                  key={segment.id}
                  type="button"
                  aria-label={`${roleLabel(segment.role)} ${segment.source}`}
                  aria-pressed={segment.id === selectedId}
                  className={`h-full border-r border-well ${segment.role === "a_roll" ? "bg-talking" : "bg-scenic"} ${
                    segment.id === selectedId ? "outline outline-2 outline-ink" : ""
                  }`}
                  style={{ width: `${width}%` }}
                  onClick={() => select(segment.id)}
                />
              );
            })}
            <input
              aria-label="Scrub the cut"
              className="absolute inset-x-0 bottom-0"
              type="range"
              min={0}
              max={total}
              step={0.1}
              value={playhead}
              onChange={(event) => setPlayhead(Number(event.target.value))}
            />
          </div>
        )}
        <p className="px-4 pb-2 text-xs text-muted">
          Space play · J K L shuttle · Delete remove · L lock · [ ] nudge · ⌘Z undo
        </p>
      </div>
      {selected ? (
        <aside className="w-64 border-l border-line p-3 text-sm">
          <p className={selected.role === "a_roll" ? "text-talking" : "text-scenic"}>{roleLabel(selected.role)}</p>
          <p className="mt-1 font-medium">{selected.source}</p>
          <p className="mt-2 text-muted">
            In {clock(selected.in_s)} · Out {clock(selected.out_s)}
          </p>
          <p className="mt-3">{selected.reason}</p>
        </aside>
      ) : null}
    </section>
  );
}

function Transcript() {
  return (
    <div className="flex-1 overflow-auto px-4 py-2 text-sm">
      {sampleWords.map((word) => (
        <p key={word.start} className="py-1">
          <span className="mr-3 text-muted">{clock(word.start)}</span>
          {word.scenic ? <span className="text-scenic">Scenic · </span> : null}
          {word.text}
        </p>
      ))}
      <p className="pt-2 text-xs text-muted">Struck words are removed from the cut. Select words and press Delete to strike them.</p>
    </div>
  );
}
