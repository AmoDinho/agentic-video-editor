import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, EDL, Segment } from "../api";
import ProjectNav from "./ProjectNav";

export default function Review() {
  const { id } = useParams();
  const video = useRef<HTMLVideoElement>(null);
  const [edl, setEdl] = useState<EDL | null>(null);
  const [style, setStyle] = useState<any>(null);
  const [sel, setSel] = useState<Segment | null>(null);
  const [note, setNote] = useState("");
  const [log, setLog] = useState("");

  async function load() {
    setEdl(await api<EDL>(`/projects/${id}/edl`));
    try {
      setStyle(await api(`/projects/${id}/style`));
    } catch {
      setStyle(null);
    }
  }
  useEffect(() => {
    load().catch(() => setEdl(null));
  }, [id]);

  function jump(seg: Segment) {
    setSel(seg);
    const t = edl!.segments.slice(0, edl!.segments.indexOf(seg)).reduce((a, s) => a + (s.out_s - s.in_s), 0);
    if (video.current) video.current.currentTime = t;
  }

  async function patch(op: string, extra: Record<string, unknown> = {}) {
    if (!sel) return;
    setEdl(
      await api<EDL>(`/projects/${id}/edl`, {
        method: "PATCH",
        body: JSON.stringify({ op, segment_id: sel.id, ...extra }),
      })
    );
  }

  async function regenerate() {
    setLog("regenerating…");
    await api(`/projects/${id}/edit`, {
      method: "POST",
      body: JSON.stringify({ note, locked_ids: edl?.segments.filter((s) => s.locked).map((s) => s.id) || [] }),
    });
    const src = new EventSource(`/projects/${id}/events`);
    src.onmessage = (ev) => {
      setLog(ev.data);
      try {
        const data = JSON.parse(ev.data);
        if (data.stage === "done" || data.stage === "idle") {
          src.close();
          load();
        }
      } catch {
        /* ignore */
      }
    };
  }

  const total = edl?.segments.reduce((a, s) => a + (s.out_s - s.in_s), 0) || 0;
  const cpm = total ? ((edl!.segments.length - 1) / total) * 60 : 0;
  const median = edl && edl.segments.length
    ? [...edl.segments.map((s) => s.out_s - s.in_s)].sort((a, b) => a - b)[Math.floor(edl.segments.length / 2)]
    : 0;

  return (
    <div>
      <ProjectNav id={id!} />
      <h1>Review</h1>
      {!edl && <div className="muted">No cut yet. Run an edit first.</div>}
      {edl && (
        <>
          <video className="player" ref={video} controls src={`/projects/${id}/preview`} />
          <div className="strip">
            {edl.segments.map((s) => (
              <div
                key={s.id}
                className={`seg ${s.role} ${s.locked ? "locked" : ""}`}
                style={{ flex: Math.max(s.out_s - s.in_s, 0.3) }}
                title={s.reason}
                onClick={() => jump(s)}
              />
            ))}
          </div>
          <div className="stats">
            <div className="card">
              Runtime {total.toFixed(1)}s / {(edl.target_duration_s || 0).toFixed(1)}s
              <div className="muted">ref {(style?.runtime_s || 0).toFixed(1)}s</div>
            </div>
            <div className="card">
              Cuts/min {cpm.toFixed(1)}
              <div className="muted">ref {(style?.cuts_per_minute || 0).toFixed(1)}</div>
            </div>
            <div className="card">
              Median shot {median.toFixed(2)}s
              <div className="muted">ref {(style?.shot_length?.median || 0).toFixed(2)}s</div>
            </div>
          </div>
          <div className="row">
            <div className="panel" style={{ flex: 1 }}>
              {sel ? (
                <>
                  <h2>{sel.id} · {sel.role}</h2>
                  <div className="muted">{sel.source}</div>
                  <div>
                    {sel.in_s.toFixed(2)} → {sel.out_s.toFixed(2)} ({(sel.out_s - sel.in_s).toFixed(2)}s)
                  </div>
                  <p>{sel.reason}</p>
                  <div className="row">
                    <button className="secondary" onClick={() => patch("lock")}>Lock</button>
                    <button className="secondary" onClick={() => patch("unlock")}>Unlock</button>
                    <button className="danger" onClick={() => patch("remove")}>Remove</button>
                    <button
                      className="secondary"
                      onClick={() => patch("nudge", { in_s: sel.in_s + 0.1, out_s: sel.out_s })}
                    >
                      Nudge in +
                    </button>
                    <button
                      className="secondary"
                      onClick={() => patch("nudge", { in_s: Math.max(0, sel.in_s - 0.1), out_s: sel.out_s })}
                    >
                      Nudge in −
                    </button>
                  </div>
                </>
              ) : (
                <div className="muted">Select a segment</div>
              )}
            </div>
            <div className="panel" style={{ flex: 1 }}>
              <h2>Revise with a note</h2>
              <textarea rows={4} value={note} onChange={(e) => setNote(e.target.value)} placeholder="shorter overall, more scenery in the middle" />
              <button onClick={regenerate}>Regenerate (keep locked)</button>
              <div className="muted">{log}</div>
              <p className="muted">{edl.notes}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
