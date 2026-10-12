import { analyseClips, generateClips, refineClips, type ClipCard } from "./fixtures";
import { useEditor, type ScreenId } from "../store";

const lists: Record<ScreenId, ClipCard[]> = {
  empty: [],
  analyse: analyseClips,
  generate: generateClips,
  compare: generateClips,
  refine: refineClips,
  transcript: refineClips,
};

export function ClipList() {
  const screen = useEditor((state) => state.screen);
  const leftTab = useEditor((state) => state.leftTab);
  const setLeftTab = useEditor((state) => state.setLeftTab);
  const selectedId = useEditor((state) => state.selectedId);
  const select = useEditor((state) => state.select);
  const clips = lists[screen];
  const groups = group(clips);

  return (
    <aside className="flex w-[19%] min-w-[220px] flex-col border-r border-line">
      <div className="flex items-center gap-4 border-b border-line px-3 text-sm">
        <button type="button" className={`py-3 ${leftTab === "clips" ? "border-b border-ink" : "text-muted"}`} onClick={() => setLeftTab("clips")}>
          Clips {screen === "analyse" ? "30" : ""}
        </button>
        <button type="button" className={`py-3 ${leftTab === "styles" ? "border-b border-ink" : "text-muted"}`} onClick={() => setLeftTab("styles")}>
          Styles
        </button>
        {screen === "analyse" ? <span className="ml-auto text-muted">31:40 total</span> : null}
      </div>
      {leftTab === "styles" ? (
        <p className="p-4 text-sm text-muted">Saved styles live with the project. Pick one in the centre.</p>
      ) : clips.length === 0 ? (
        <div className="grid flex-1 place-items-center px-6 text-center text-sm text-muted">
          <div>
            <p className="text-ink">No clips yet</p>
            <p className="mt-1">Clips appear here grouped by day and camera, in shooting order.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-2 text-sm">
          {groups.map((group) => (
            <section key={group.name || "all"}>
              {group.name ? (
                <header className="flex justify-between px-1 py-2 text-xs tracking-wide text-muted">
                  <span>{group.name}</span>
                  <span>{group.clips.length} clips</span>
                </header>
              ) : null}
              <ul className="space-y-1">
                {group.clips.map((clip) => (
                  <li key={clip.name}>
                    <button
                      type="button"
                      onClick={() => select(clip.name)}
                      className={`press w-full rounded-md px-2 py-2 text-left ${
                        selectedId === clip.name ? "outline outline-1 outline-paper" : "hover-raise"
                      } ${clip.error ? "outline outline-1 outline-danger" : ""}`}
                    >
                      <span className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${dot(clip.kind)}`} />
                        <span className="truncate">{clip.name}</span>
                        {clip.time ? <span className="ml-auto text-muted">{clip.time}</span> : null}
                      </span>
                      <span className="mt-1 flex flex-wrap items-center gap-2 pl-4 text-xs text-muted">
                        <Kind clip={clip} />
                        {clip.duration && screen !== "generate" ? <span>{clip.duration}</span> : null}
                        {clip.used ? <span>{clip.used}</span> : null}
                      </span>
                      {clip.flag ? <span className="mt-1 block pl-4 text-xs text-muted">{clip.flag}</span> : null}
                      {clip.error ? <span className="mt-1 block pl-4 text-xs text-danger">{clip.error}</span> : null}
                      {clip.progress ? <span className="mt-1 block pl-4 text-xs text-agent">{clip.progress}</span> : null}
                      {clip.error ? (
                        <span className="mt-2 flex gap-2 pl-4">
                          <span className="rounded bg-raised px-2 py-0.5 text-xs">Retry</span>
                          <span className="rounded px-2 py-0.5 text-xs text-muted">Exclude</span>
                        </span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </aside>
  );
}

function Kind({ clip }: { clip: ClipCard }) {
  if (clip.kind === "Talking") return <span className="rounded-full bg-talking/15 px-1.5 text-talking">Talking</span>;
  if (clip.kind === "Scenic") return <span className="rounded-full bg-scenic/15 px-1.5 text-scenic">Scenic</span>;
  return <span>{clip.kind}</span>;
}

function dot(kind: ClipCard["kind"]) {
  if (kind === "Talking") return "bg-talking";
  if (kind === "Scenic") return "bg-scenic";
  if (kind === "Analysing") return "bg-agent";
  return "bg-muted";
}

function group(clips: ClipCard[]) {
  const out: { name: string; clips: ClipCard[] }[] = [];
  for (const clip of clips) {
    const last = out[out.length - 1];
    if (!last || last.name !== clip.group) out.push({ name: clip.group, clips: [clip] });
    else last.clips.push(clip);
  }
  return out;
}
