import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import ProjectNav from "./ProjectNav";

export default function Run() {
  const { id } = useParams();
  const nav = useNavigate();
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const es = useRef<EventSource | null>(null);

  function listen() {
    es.current?.close();
    const src = new EventSource(`/projects/${id}/events`);
    es.current = src;
    src.onmessage = (ev) => {
      setLog((l) => [...l.slice(-200), ev.data]);
      try {
        const data = JSON.parse(ev.data);
        if (data.stage === "idle" && data.status === "complete") {
          setBusy(false);
          src.close();
        }
        if (data.stage === "done" && data.status === "complete" && data.kind !== "analyze") {
          nav(`/p/${id}/review`);
        }
      } catch {
        /* ignore */
      }
    };
  }

  useEffect(() => () => es.current?.close(), []);

  async function analyze() {
    setBusy(true);
    setLog([]);
    await api(`/projects/${id}/analyze`, { method: "POST" });
    listen();
  }
  async function edit(mode: string) {
    setBusy(true);
    setLog([]);
    await api(`/projects/${id}/edit`, { method: "POST", body: JSON.stringify({ mode }) });
    listen();
  }

  return (
    <div>
      <ProjectNav id={id!} />
      <h1>Run</h1>
      <div className="row">
        <button disabled={busy} onClick={analyze}>Analyze</button>
        <button disabled={busy} onClick={() => edit("heuristic")}>Heuristic edit</button>
        <button disabled={busy} onClick={() => edit("agent")}>Agent edit</button>
      </div>
      <p className="muted">Progress per file, then each agent iteration.</p>
      <div className="log">{log.join("\n")}</div>
    </div>
  );
}
