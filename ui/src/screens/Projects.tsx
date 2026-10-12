import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Project } from "../api";

export default function Projects() {
  const [rows, setRows] = useState<Project[]>([]);
  useEffect(() => {
    api<Project[]>("/projects").then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Projects</h1>
        <Link className="btn" to="/new">New project</Link>
      </div>
      <div className="cards">
        {rows.map((p) => (
          <Link className="card" key={p.id} to={`/p/${p.id}/run`}>
            <h2>{p.name}</h2>
            <div className="muted">{p.clip_count ?? 0} clips</div>
            <div className="muted">
              {p.runtime_s ? `${p.runtime_s.toFixed(1)}s cut` : "no cut yet"}
            </div>
            <div className="muted">{p.last_export ? `exported ${p.last_export}` : "not exported"}</div>
          </Link>
        ))}
        {rows.length === 0 && <div className="muted">No projects yet.</div>}
      </div>
    </div>
  );
}
