import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NavLink, Route, Routes } from "react-router-dom";
import { sampleCut } from "./workspace/sample";
import { Workspace } from "./workspace/Workspace";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/settings" element={<SettingsLink />} />
        <Route path="/p/new" element={<Workspace empty />} />
        <Route path="/p/:id" element={<Workspace cut={sampleCut} />} />
      </Routes>
    </QueryClientProvider>
  );
}

function ProjectList() {
  return (
    <main className="mx-auto max-w-3xl p-10">
      <h1 className="text-2xl">Projects</h1>
      <p className="mt-2 text-muted">A project is a folder of clips and a style.</p>
      <div className="mt-6 flex gap-3">
        <NavLink to="/p/new" className="press rounded-md bg-paper px-3 py-2 text-sm text-page">
          New project
        </NavLink>
        <NavLink to="/p/demo" className="press rounded-md bg-raised px-3 py-2 text-sm">
          Open the sample cut
        </NavLink>
      </div>
    </main>
  );
}

function SettingsLink() {
  return (
    <main className="mx-auto max-w-3xl p-10">
      <NavLink to="/" className="text-sm text-talking">
        Back to project
      </NavLink>
      <h1 className="mt-4 text-2xl">Settings</h1>
      <p className="mt-2 text-muted">Media folders, models, and keys land here. Source files stay read-only.</p>
    </main>
  );
}
