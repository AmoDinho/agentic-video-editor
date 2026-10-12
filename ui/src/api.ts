export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Project = {
  id: string;
  name: string;
  clips_dir: string;
  reference_path: string;
  target_duration_s: number;
  brief: string;
  clip_count?: number;
  runtime_s?: number | null;
  last_export?: string | null;
  has_edl?: boolean;
  has_preview?: boolean;
};

export type Segment = {
  id: string;
  source: string;
  in_s: number;
  out_s: number;
  audio: string;
  role: "a_roll" | "b_roll";
  reason: string;
  locked: boolean;
};

export type EDL = {
  version: number;
  project_id: string;
  output: { width: number; height: number; fps: number; audio_rate: number };
  target_duration_s: number;
  segments: Segment[];
  notes: string;
};

export type MediaItem = {
  path: string;
  name: string;
  duration_s: number;
  shot_at: string;
  status: string;
  hash?: string;
  quality_flags: string[];
  included: boolean;
  proxy?: string;
};
