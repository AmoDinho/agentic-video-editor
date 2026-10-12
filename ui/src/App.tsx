import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, Route, Routes, useParams } from "react-router-dom";
import { useEditor, type ScreenId } from "./store";
import { SettingsPage } from "./workspace/SettingsPage";
import { Workspace } from "./workspace/Workspace";

const queryClient = new QueryClient();
const screens: ScreenId[] = ["empty", "analyse", "generate", "compare", "refine", "transcript"];

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/p/:screen" element={<ProjectRoute />} />
      </Routes>
    </QueryClientProvider>
  );
}

function ProjectRoute() {
  const { screen = "empty" } = useParams();
  const setOverlay = useEditor((state) => state.setOverlay);
  const known = screens.includes(screen as ScreenId) ? (screen as ScreenId) : "analyse";
  useEffect(() => {
    if (screen === "jobs") setOverlay("jobs");
    if (screen === "cloud") setOverlay("cloud");
    if (screen === "cloud-failed") setOverlay("cloud-failed");
    if (screen === "export") setOverlay("export");
  }, [screen, setOverlay]);
  const shown: ScreenId = screen === "jobs" || screen === "cloud" || screen === "cloud-failed" ? "analyse" : screen === "export" ? "refine" : known;
  return <Workspace screen={shown} />;
}

function ProjectList() {
  return (
    <main className="mx-auto max-w-3xl p-10">
      <h1 className="text-2xl">Projects</h1>
      <p className="mt-2 text-muted">A project is a folder of clips and a style.</p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link to="/p/empty" className="press rounded-md bg-paper px-3 py-2 text-sm text-page">
          New project
        </Link>
        <Link to="/p/analyse" className="press rounded-md bg-raised px-3 py-2 text-sm">
          Wild Coast road trip
        </Link>
        <Link to="/settings" className="press rounded-md px-3 py-2 text-sm text-talking">
          Settings
        </Link>
      </div>
    </main>
  );
}
