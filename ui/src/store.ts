import { create } from "zustand";

export type Role = "a_roll" | "b_roll";

export type Segment = {
  id: string;
  source: string;
  in_s: number;
  out_s: number;
  role: Role;
  reason: string;
  locked: boolean;
  section?: string;
};

export type Cut = {
  id: string;
  name: string;
  runtime_s: number;
  segments: Segment[];
};

type EditorState = {
  theme: "dark" | "light";
  projectName: string;
  selectedId: string | null;
  playing: boolean;
  playhead: number;
  bottomTab: "timeline" | "transcript" | "footage";
  leftTab: "clips" | "styles";
  jobsOpen: boolean;
  setTheme: (theme: "dark" | "light") => void;
  select: (id: string | null) => void;
  togglePlay: () => void;
  setPlayhead: (seconds: number) => void;
  setBottomTab: (tab: EditorState["bottomTab"]) => void;
  setLeftTab: (tab: EditorState["leftTab"]) => void;
  setJobsOpen: (open: boolean) => void;
};

export const useEditor = create<EditorState>((set) => ({
  theme: "dark",
  projectName: "Untitled project",
  selectedId: null,
  playing: false,
  playhead: 0,
  bottomTab: "timeline",
  leftTab: "clips",
  jobsOpen: false,
  setTheme: (theme) => set({ theme }),
  select: (selectedId) => set({ selectedId }),
  togglePlay: () => set((state) => ({ playing: !state.playing })),
  setPlayhead: (playhead) => set({ playhead }),
  setBottomTab: (bottomTab) => set({ bottomTab }),
  setLeftTab: (leftTab) => set({ leftTab }),
  setJobsOpen: (jobsOpen) => set({ jobsOpen }),
}));

export function roleLabel(role: Role): "Talking" | "Scenic" {
  return role === "a_roll" ? "Talking" : "Scenic";
}

export function clock(seconds: number): string {
  const sign = seconds < 0 ? "-" : "";
  const total = Math.max(0, Math.floor(Math.abs(seconds)));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${sign}${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
