import { useEditor, roleLabel, type Segment } from "../store";

export function MediaBin({ segments, empty }: { segments: Segment[]; empty: boolean }) {
  const { leftTab, setLeftTab } = useEditor();
  return (
    <aside className="flex w-[19%] min-w-[220px] flex-col border-r border-line">
      <div className="flex gap-4 border-b border-line px-4 text-sm">
        {(["clips", "styles"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            className={`py-3 capitalize ${leftTab === tab ? "border-b border-ink" : "text-muted"}`}
            onClick={() => setLeftTab(tab)}
          >
            {tab === "clips" ? "Clips" : "Styles"}
          </button>
        ))}
      </div>
      {empty || leftTab === "styles" ? (
        <div className="grid flex-1 place-items-center px-6 text-center text-sm text-muted">
          <div>
            <p className="text-ink">{leftTab === "styles" ? "No saved styles" : "No clips yet"}</p>
            <p className="mt-1">
              {leftTab === "styles"
                ? "A style is a reference video, or a cut you save from an earlier project."
                : "Clips appear here grouped by day and camera, in shooting order."}
            </p>
          </div>
        </div>
      ) : (
        <ul className="flex-1 overflow-auto p-2">
          {segments.map((segment) => (
            <li key={segment.id} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover-raise">
              <span className={`h-2 w-2 rounded-full ${segment.role === "a_roll" ? "bg-talking" : "bg-scenic"}`} />
              <span className="truncate">{segment.source}</span>
              <span className="ml-auto text-muted">{roleLabel(segment.role)}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
