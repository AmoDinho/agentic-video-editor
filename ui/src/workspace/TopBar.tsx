import { Film, Sun } from "lucide-react";
import { Link } from "react-router-dom";
import { useEditor, type ScreenId } from "../store";

const status: Record<ScreenId, [string, string]> = {
  empty: ["Nothing running", ""],
  analyse: ["Analysing 9 of 30 clips", "about 6 min left"],
  generate: ["Generating · Section 3 of 5", "about 4 min left"],
  compare: ["3 cuts ready", "took 9 min 40 s"],
  refine: ["All changes saved · v7", ""],
  transcript: ["All changes saved · v8", ""],
};

export function TopBar() {
  const screen = useEditor((state) => state.screen);
  const projectName = useEditor((state) => state.projectName);
  const overlay = useEditor((state) => state.overlay);
  const setOverlay = useEditor((state) => state.setOverlay);
  const theme = useEditor((state) => state.theme);
  const setTheme = useEditor((state) => state.setTheme);
  const [label, remaining] = overlay === "jobs" ? ["2 jobs running", "about 5 min left"] : overlay === "export" ? ["Exporting · 42%", "about 2 min left"] : status[screen];

  return (
    <header className="grid h-[51px] grid-cols-[1fr_auto_1fr] items-center border-b border-line px-4">
      <div className="flex items-center gap-2 text-sm">
        <Film size={16} />
        <Link to="/" className="text-talking">
          Projects
        </Link>
        <span className="text-muted">/</span>
        <span className="font-medium">{projectName}</span>
      </div>
      <button type="button" className="press flex items-center gap-2 rounded-full bg-raised px-3 py-1 text-sm" onClick={() => setOverlay(overlay === "jobs" ? null : "jobs")} aria-expanded={overlay === "jobs"}>
        <span className="h-1.5 w-1.5 rounded-full bg-agent" />
        <span>{label}</span>
        {remaining ? <span className="text-muted">{remaining}</span> : null}
      </button>
      <div className="flex items-center justify-end gap-2">
        {screen === "refine" || screen === "transcript" ? (
          <button type="button" className="press rounded-md px-2 py-1 text-sm" onClick={() => setOverlay(overlay === "versions" ? null : "versions")}>
            Versions
          </button>
        ) : null}
        <button type="button" aria-label={theme === "dark" ? "Switch to light" : "Switch to dark"} className="press grid h-8 w-8 place-items-center rounded-md" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          <Sun size={16} />
        </button>
        <button type="button" className="press rounded-md bg-[#6c6b6b] px-3 py-1.5 text-sm text-[#131417]" onClick={() => setOverlay("export")}>
          Export video
        </button>
      </div>
    </header>
  );
}
