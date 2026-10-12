import { useEffect, useState } from "react";
import { api } from "../api";

type Entry = { name: string; path: string; type: string; is_video: boolean };
type Listing = { path: string; parent: string; entries: Entry[] };

export default function Browser({
  onPick,
  onClose,
  files,
}: {
  onPick: (path: string) => void;
  onClose: () => void;
  files?: boolean;
}) {
  const [data, setData] = useState<Listing | null>(null);
  const [path, setPath] = useState("");
  useEffect(() => {
    api<Listing>(`/browse?path=${encodeURIComponent(path)}`).then(setData);
  }, [path]);
  if (!data) return null;
  return (
    <div className="panel" style={{ marginTop: 16, maxWidth: 640 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>{data.path}</h2>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
      <div className="browse">
        <button onClick={() => setPath(data.parent)}>.. parent</button>
        {data.entries.map((e) => (
          <button
            key={e.path}
            onClick={() => {
              if (e.type === "dir") setPath(e.path);
              else if (files) onPick(e.path);
            }}
          >
            {e.type === "dir" ? "▸" : "●"} {e.name}
          </button>
        ))}
      </div>
      {!files && (
        <button style={{ marginTop: 8 }} onClick={() => onPick(data.path)}>
          Use this folder
        </button>
      )}
    </div>
  );
}
