import { NavLink, Route, Routes } from "react-router-dom";
import Projects from "./screens/Projects";
import NewProject from "./screens/NewProject";
import MediaBin from "./screens/MediaBin";
import Run from "./screens/Run";
import Review from "./screens/Review";
import Export from "./screens/Export";
import Settings from "./screens/Settings";

export default function App() {
  return (
    <div className="app">
      <aside>
        <div className="brand">AVE</div>
        <nav>
          <NavLink to="/">Projects</NavLink>
          <NavLink to="/new">New project</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<Projects />} />
          <Route path="/new" element={<NewProject />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/p/:id/media" element={<MediaBin />} />
          <Route path="/p/:id/run" element={<Run />} />
          <Route path="/p/:id/review" element={<Review />} />
          <Route path="/p/:id/export" element={<Export />} />
        </Routes>
      </main>
    </div>
  );
}
