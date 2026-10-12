import { useEffect, useState } from "react";
import { api } from "../api";

export default function Settings() {
  const [data, setData] = useState<any>(null);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  useEffect(() => {
    api<any>("/settings").then((s) => {
      setData(s);
      setProvider(s.llm.provider);
      setModel(s.llm.model);
    });
  }, []);
  async function save() {
    const s = await api<any>("/settings", {
      method: "PUT",
      body: JSON.stringify({ provider, model, api_key: key || null }),
    });
    setData(s);
    setKey("");
  }
  async function clear() {
    setData(await api("/settings/cache/clear", { method: "POST" }));
  }
  if (!data) return null;
  const gb = (data.cache_bytes / 1e9).toFixed(2);
  return (
    <div>
      <h1>Settings</h1>
      <div className="panel" style={{ maxWidth: 560 }}>
        {data.cloud_mode && (
          <p className="error">Cloud mode: transcripts, captions and stats leave this machine. Video stays local.</p>
        )}
        <label>
          Provider
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="ollama">ollama (local)</option>
            <option value="anthropic">anthropic</option>
            <option value="openai">openai</option>
            <option value="openai_compatible">openai compatible</option>
          </select>
        </label>
        <label>
          Model
          <input value={model} onChange={(e) => setModel(e.target.value)} />
        </label>
        <label>
          API key (Keychain, never written to config)
          <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder={data.has_api_key ? "•••• saved" : ""} />
        </label>
        <div className="row">
          <button onClick={save}>Save</button>
          <button className="secondary" onClick={clear}>Clear cache ({gb} GB)</button>
        </div>
        <p className="muted">Ollama: {data.hardware.ollama ? "reachable" : "not running"}</p>
        <p className="muted">FFmpeg: {data.hardware.ffmpeg || "missing"}</p>
      </div>
    </div>
  );
}
