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

export type ScreenId = "empty" | "analyse" | "generate" | "compare" | "refine" | "transcript";
export type Overlay = null | "jobs" | "cloud" | "export" | "versions" | "cloud-failed";

type EditorState = {
  theme: "dark" | "light";
  projectName: string;
  screen: ScreenId;
  overlay: Overlay;
  variant: "tight" | "matched" | "relaxed";
  selectedId: string | null;
  playing: boolean;
  playhead: number;
  bottomTab: "timeline" | "transcript" | "footage" | "compare";
  leftTab: "clips" | "styles";
  struck: number[];
  setTheme: (theme: "dark" | "light") => void;
  setScreen: (screen: ScreenId) => void;
  setOverlay: (overlay: Overlay) => void;
  setVariant: (variant: EditorState["variant"]) => void;
  select: (id: string | null) => void;
  togglePlay: () => void;
  setPlayhead: (seconds: number) => void;
  setBottomTab: (tab: EditorState["bottomTab"]) => void;
  setLeftTab: (tab: EditorState["leftTab"]) => void;
  toggleStrike: (index: number) => void;
};

export const useEditor = create<EditorState>((set) => ({
  theme: "dark",
  projectName: "Untitled project",
  screen: "empty",
  overlay: null,
  variant: "matched",
  selectedId: "IMG_2047.MOV",
  playing: false,
  playhead: 24.1,
  bottomTab: "timeline",
  leftTab: "clips",
  struck: [],
  setTheme: (theme) => set({ theme }),
  setScreen: (screen) =>
    set({
      screen,
      projectName: screen === "empty" ? "Untitled project" : "Wild Coast road trip",
      overlay: null,
      bottomTab: screen === "analyse" ? "footage" : screen === "compare" ? "compare" : screen === "transcript" ? "transcript" : "timeline",
    }),
  setOverlay: (overlay) => set({ overlay }),
  setVariant: (variant) => set({ variant }),
  select: (selectedId) => set({ selectedId }),
  togglePlay: () => set((state) => ({ playing: !state.playing })),
  setPlayhead: (playhead) => set({ playhead }),
  setBottomTab: (bottomTab) => set({ bottomTab }),
  setLeftTab: (leftTab) => set({ leftTab }),
  toggleStrike: (index) =>
    set((state) => ({
      struck: state.struck.includes(index) ? state.struck.filter((item) => item !== index) : [...state.struck, index],
    })),
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
