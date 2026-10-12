import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Browser from "./Browser";

export default function NewProject() {
  const nav = useNavigate();
  const [name, setName] = useState("Untitled");
  const [clips, setClips] = useState("");
  const [ref, setRef] = useState("");
  const [target, setTarget] = useState(60);
  const [brief, setBrief] = useState("");
  const [pick, setPick] = useState<"clips" | "ref" | null>(null);
  const [err, setErr] = useState("");

  async function create() {
    setErr("");
    try {
      const p = await api<{ id: string }>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name,
          clips_dir: clips,
          reference_path: ref,
          target_duration_s: target,
          brief,
        }),
      });
      nav(`/p/${p.id}/media`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <div>
      <h1>New project</h1>
      <div className="panel" style={{ maxWidth: 640 }}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Clips folder
          <div className="row">
            <input value={clips} onChange={(e) => setClips(e.target.value)} />
            <button className="secondary" type="button" onClick={() => setPick("clips")}>
              Browse
            </button>
          </div>
        </label>
        <label>
          Reference video
          <div className="row">
            <input value={ref} onChange={(e) => setRef(e.target.value)} />
            <button className="secondary" type="button" onClick={() => setPick("ref")}>
              Browse
            </button>
          </div>
        </label>
        <label>
          Target length (seconds)
          <input type="number" value={target} onChange={(e) => setTarget(Number(e.target.value))} />
        </label>
        <label>
          Brief (optional)
          <textarea rows={4} value={brief} onChange={(e) => setBrief(e.target.value)} />
        </label>
        {err && <div className="error">{err}</div>}
        <button type="button" onClick={create}>Create</button>
      </div>
      {pick && (
        <Browser
          files={pick === "ref"}
          onClose={() => setPick(null)}
          onPick={(p) => {
            if (pick === "clips") setClips(p);
            else setRef(p);
            setPick(null);
          }}
        />
      )}
    </div>
  );
}
