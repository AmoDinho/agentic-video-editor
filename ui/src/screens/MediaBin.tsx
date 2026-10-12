import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, MediaItem } from "../api";
import ProjectNav from "./ProjectNav";

export default function MediaBin() {
  const { id } = useParams();
  const [rows, setRows] = useState<MediaItem[]>([]);
  async function load() {
    if (!id) return;
    setRows(await api<MediaItem[]>(`/projects/${id}/media`));
  }
  useEffect(() => {
    load();
  }, [id]);
  async function toggle(item: MediaItem) {
    const excluded = rows.filter((r) => (r.path === item.path ? r.included : !r.included)).map((r) => r.path);
    await api(`/projects/${id}/media`, { method: "PUT", body: JSON.stringify({ excluded }) });
    load();
  }
  return (
    <div>
      <ProjectNav id={id!} />
      <h1>Media bin</h1>
      <div className="grid">
        {rows.map((r) => (
          <div className="card row" key={r.path} style={{ justifyContent: "space-between" }}>
            <div>
              <div>{r.name}</div>
              <div className="muted">
                {(r.duration_s || 0).toFixed(1)}s · {r.shot_at?.slice(0, 19)} · {r.status}
              </div>
              {r.quality_flags.length > 0 && (
                <div className="error">{r.quality_flags.join(", ")}</div>
              )}
            </div>
            <button className="secondary" onClick={() => toggle(r)}>
              {r.included ? "Exclude" : "Include"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
