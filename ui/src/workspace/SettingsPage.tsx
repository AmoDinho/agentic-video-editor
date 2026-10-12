import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useEditor } from "../store";

const folders = [
  { path: "~/Movies/Footage 2026", clips: "412 clips" },
  { path: "/Volumes/T7/GoPro", clips: "96 clips" },
  { path: "~/Desktop/Phone exports", clips: "New · not saved", fresh: true },
];

export function SettingsPage() {
  const theme = useEditor((state) => state.theme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const [section, setSection] = useState("Media folders");
  const [fast, setFast] = useState(false);
  return (
    <div className="flex h-full bg-page text-ink">
      <aside className="w-56 border-r border-line p-4">
        <Link to="/p/analyse" className="text-sm text-talking">
          Back to project
        </Link>
        <h1 className="mt-4 text-lg">Settings</h1>
        <nav className="mt-4 space-y-1 text-sm">
          {["Media folders", "Models", "API keys", "Exports", "This Mac", "Appearance"].map((item) => (
            <button
              key={item}
              type="button"
              className={`block w-full rounded-md px-3 py-2 text-left ${section === item ? "bg-raised" : "text-muted"}`}
              onClick={() => setSection(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto px-8 py-6">
        <section>
          <h2 className="text-xl">Media folders</h2>
          <p className="mt-1 text-sm text-muted">The app can only see footage in these folders. They're read-only: source files are never changed.</p>
          <ul className="mt-4 space-y-2">
            {folders.map((folder) => (
              <li key={folder.path} className={`flex items-center rounded-lg px-3 py-3 ${folder.fresh ? "outline outline-dashed outline-agent" : "bg-raised"}`}>
                <span>{folder.path}</span>
                <span className={`ml-auto mr-4 text-sm ${folder.fresh ? "text-agent" : "text-muted"}`}>{folder.clips}</span>
                <button type="button" className="text-sm">
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-3">
            <button type="button" className="press rounded-md bg-raised px-3 py-2 text-sm">
              + Add folder
            </button>
            <button type="button" className="press rounded-md bg-paper px-3 py-2 text-sm text-page">
              Save folders
            </button>
            <span className="text-sm text-muted">Saving restarts the editor's background services (about 10 s). Running jobs pause and resume.</span>
          </div>
        </section>
        <section className="mt-8">
          <h2 className="text-xl">Models</h2>
          <p className="mt-1 text-sm text-muted">The default for every project. You can switch to the cloud for a single run next to Generate cuts.</p>
          <div className="mt-4 space-y-3 text-sm">
            <Row label="Editing agent" value="Local · Qwen 2.5 7B (Docker Model Runner)" pill="Running on GPU" />
            <Row label="Shot descriptions" value="Local · vision model (Docker Model Runner)" pill="Running on GPU" />
            <Row label="Transcription" value="Whisper small · CPU" pill="CPU" quiet />
          </div>
        </section>
        <section className="mt-8">
          <h2 className="text-xl">API keys</h2>
          <p className="mt-1 text-sm text-muted">Stored encrypted on this Mac. Never logged, never shown again after saving.</p>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex items-center rounded-lg bg-raised px-3 py-3">
              <span className="w-24">Anthropic</span>
              <span>sk-ant-········1234</span>
              <span className="ml-auto rounded-full bg-agent/20 px-2 py-0.5 text-agent">Saved</span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-raised px-3 py-3">
              <span className="w-24">OpenAI</span>
              <input className="flex-1 bg-transparent" placeholder="Paste a key" aria-label="OpenAI key" />
              <button type="button" className="rounded-md bg-page px-3 py-1">
                Save key
              </button>
            </div>
          </div>
        </section>
        <section className="mt-8">
          <h2 className="text-xl">This Mac</h2>
          <p className="mt-1 text-sm text-muted">MacBook Pro · M3 Pro · 18 GB. Time estimates are measured here and improve with each run.</p>
          <div className="mt-4 space-y-2">
            <div className="flex items-center rounded-lg bg-raised px-3 py-3">
              <div>
                <p>Fast mode</p>
                <p className="text-sm text-muted">Runs transcription and search on the Mac's GPU. Needs one extra install.</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={fast}
                className={`press ml-auto h-6 w-10 rounded-full ${fast ? "bg-agent" : "bg-line"}`}
                onClick={() => setFast(!fast)}
              />
            </div>
            <div className="flex items-center rounded-lg bg-raised px-3 py-3">
              <div>
                <p>Calibration</p>
                <p className="text-sm text-muted">Last run today 09:14 · transcription 0.21× real time · agent 24 tokens/s</p>
              </div>
              <button type="button" className="press ml-auto rounded-md bg-page px-3 py-1 text-sm">
                Run again (20 s)
              </button>
            </div>
          </div>
        </section>
        {section === "Appearance" ? <p className="mt-8 text-sm text-muted">Light and dark follow the sun in the workspace. Contrast stays AA in both.</p> : null}
        {section === "Exports" ? <p className="mt-8 text-sm text-muted">Exports land in ~/Movies/Rough Cuts. Source files are never written.</p> : null}
      </main>
    </div>
  );
}

function Row({ label, value, pill, quiet }: { label: string; value: string; pill: string; quiet?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-36 text-muted">{label}</span>
      <span className="flex-1 rounded-md border border-line px-3 py-2">{value}</span>
      <span className={`rounded-full px-2 py-0.5 text-xs ${quiet ? "bg-raised text-muted" : "bg-agent/20 text-agent"}`}>{pill}</span>
    </div>
  );
}
