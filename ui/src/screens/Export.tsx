import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import ProjectNav from "./ProjectNav";

export default function Export() {
  const { id } = useParams();
  const [w, setW] = useState(1920);
  const [h, setH] = useState(1080);
  const [fps, setFps] = useState(30);
  const [dest, setDest] = useState("");
  const [log, setLog] = useState("");

  async function go() {
    setLog("exporting…");
    await api(`/projects/${id}/export`, {
      method: "POST",
      body: JSON.stringify({ width: w, height: h, fps, dest: dest || null }),
    });
    const src = new EventSource(`/projects/${id}/events`);
    src.onmessage = (ev) => {
      setLog(ev.data);
      try {
        const data = JSON.parse(ev.data);
        if (data.stage === "done" || data.stage === "idle") src.close();
      } catch {
        /* ignore */
      }
    };
  }

  return (
    <div>
      <ProjectNav id={id!} />
      <h1>Export</h1>
      <div className="panel" style={{ maxWidth: 520 }}>
        <label>
          Width
          <input type="number" value={w} onChange={(e) => setW(Number(e.target.value))} />
        </label>
        <label>
          Height
          <input type="number" value={h} onChange={(e) => setH(Number(e.target.value))} />
        </label>
        <label>
          FPS
          <input type="number" value={fps} onChange={(e) => setFps(Number(e.target.value))} />
        </label>
        <label>
          Destination folder (optional)
          <input value={dest} onChange={(e) => setDest(e.target.value)} />
        </label>
        <button onClick={go}>Export MP4 + timeline</button>
        <p className="muted">{log}</p>
      </div>
    </div>
  );
}
