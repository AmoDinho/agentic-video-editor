import { Film, Sun } from "lucide-react";
import { Link } from "react-router-dom";
import { useEditor } from "../store";

export function TopBar({ status, remaining }: { status: string; remaining: string }) {
  const { projectName, jobsOpen, setJobsOpen, theme, setTheme } = useEditor();
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
      <button
        type="button"
        className="press flex items-center gap-2 rounded-full bg-raised px-3 py-1 text-sm"
        onClick={() => setJobsOpen(!jobsOpen)}
        aria-expanded={jobsOpen}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-agent" />
        <span>{status}</span>
        <span className="text-muted">{remaining}</span>
      </button>
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          aria-label={theme === "dark" ? "Switch to light" : "Switch to dark"}
          className="press grid h-8 w-8 place-items-center rounded-md"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun size={16} />
        </button>
        <button type="button" className="press rounded-md bg-[#6c6b6b] px-3 py-1.5 text-sm text-[#131417]">
          Export video
        </button>
      </div>
    </header>
  );
}
