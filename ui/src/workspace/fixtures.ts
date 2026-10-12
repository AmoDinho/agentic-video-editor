export type ClipCard = {
  name: string;
  time: string;
  duration: string;
  kind: "Talking" | "Scenic" | "Analysing" | "Queued" | "Excluded";
  flag?: string;
  error?: string;
  progress?: string;
  group: string;
  used?: string;
};

export const analyseClips: ClipCard[] = [
  { group: "SAT 3 OCT · IPHONE", name: "IMG_2031.MOV", time: "08:52", duration: "0:42", kind: "Talking" },
  { group: "SAT 3 OCT · IPHONE", name: "IMG_2033.MOV", time: "09:10", duration: "1:18", kind: "Scenic", flag: "Shaky 0:12–0:18" },
  { group: "SAT 3 OCT · IPHONE", name: "IMG_2034.MOV", time: "09:41", duration: "2:05", kind: "Talking" },
  { group: "SAT 3 OCT · IPHONE", name: "IMG_2038.MOV", time: "11:02", duration: "0:36", kind: "Scenic" },
  { group: "SAT 3 OCT · GOPRO", name: "GOPR0190.MP4", time: "12:20", duration: "3:12", kind: "Scenic", flag: "Wind noise" },
  {
    group: "SAT 3 OCT · GOPRO",
    name: "GOPR0193.MP4",
    time: "13:05",
    duration: "1:40",
    kind: "Scenic",
    error: "Unsupported codec: convert to H.264",
  },
  {
    group: "SAT 3 OCT · GOPRO",
    name: "GOPR0194.MP4",
    time: "13:30",
    duration: "2:22",
    kind: "Talking",
    progress: "Transcribing speech · 64% · 40 s left",
  },
];

export const generateClips: ClipCard[] = [
  { group: "", name: "IMG_2031.MOV", time: "", duration: "0:42", kind: "Talking" },
  { group: "", name: "IMG_2033.MOV", time: "", duration: "1:18", kind: "Scenic" },
  { group: "", name: "IMG_2034.MOV", time: "", duration: "2:05", kind: "Talking" },
  { group: "", name: "IMG_2038.MOV", time: "", duration: "0:36", kind: "Scenic" },
  { group: "", name: "GOPR0190.MP4", time: "", duration: "3:12", kind: "Scenic" },
  { group: "", name: "GOPR0194.MP4", time: "", duration: "2:22", kind: "Talking" },
  { group: "", name: "IMG_2047.MOV", time: "", duration: "1:04", kind: "Scenic" },
  { group: "", name: "IMG_2052.MOV", time: "", duration: "0:58", kind: "Talking" },
  { group: "", name: "IMG_2055.MOV", time: "", duration: "", kind: "Analysing", progress: "70%" },
  { group: "", name: "IMG_2058.MOV", time: "", duration: "", kind: "Queued" },
];

export const refineClips: ClipCard[] = [
  { group: "", name: "IMG_2031.MOV", time: "", duration: "", kind: "Talking", used: "in cut 2×" },
  { group: "", name: "IMG_2033.MOV", time: "", duration: "", kind: "Scenic", used: "in cut 1×" },
  { group: "", name: "IMG_2034.MOV", time: "", duration: "", kind: "Talking", used: "in cut 3×" },
  { group: "", name: "IMG_2038.MOV", time: "", duration: "", kind: "Scenic", used: "not used" },
  { group: "", name: "GOPR0190.MP4", time: "", duration: "", kind: "Scenic", used: "in cut 4×" },
  { group: "", name: "GOPR0193.MP4", time: "", duration: "", kind: "Excluded", used: "codec" },
  { group: "", name: "GOPR0194.MP4", time: "", duration: "", kind: "Talking", used: "in cut 2×" },
  { group: "", name: "IMG_2047.MOV", time: "", duration: "", kind: "Scenic", used: "selected" },
  { group: "", name: "IMG_2052.MOV", time: "", duration: "", kind: "Talking", used: "in cut 1×" },
  { group: "", name: "IMG_2055.MOV", time: "", duration: "", kind: "Scenic", used: "in cut 2×" },
];

export const styles = [
  { name: "Slow travel diary", line: "About 5 cuts a minute · shots 4–8 s · 35% talking · 12 min" },
  { name: "Punchy weekend recap", line: "About 16 cuts a minute · shots 1–3 s · 50% talking · 4 min" },
];

export const variants = [
  {
    id: "tight" as const,
    title: "Tight",
    runtime: "5:48",
    blurb: "Fastest. Drops most of the village and market section.",
    cuts: "61",
    pace: "10.5 a minute",
    shots: "1.5–4 s",
    talking: "54%",
    chip: "00:00",
  },
  {
    id: "matched" as const,
    title: "Matched",
    runtime: "8:06",
    blurb: "Follows the reference pace. Every section kept.",
    cuts: "73",
    pace: "9.0 a minute",
    shots: "2–5 s",
    talking: "61%",
    chip: "03:41 · Beach camp",
    closest: true,
  },
  {
    id: "relaxed" as const,
    title: "Relaxed",
    runtime: "10:24",
    blurb: "Lets scenic shots breathe and keeps the long campfire chat.",
    cuts: "68",
    pace: "6.5 a minute",
    shots: "3–7 s",
    talking: "66%",
    chip: "00:00",
  },
];

export const versions = [
  { n: "v8", summary: "Removed 9 words in the beach chat", who: "You · transcript · just now", current: false },
  { n: "v7", summary: "Shorter intro, more beach", who: "Agent · just now · current", current: true },
  { n: "v6", summary: "Locked the camp wide shot", who: "You · 3 min ago", current: false },
  { n: "v5", summary: "Removed 2 words in the hike", who: "You · transcript · 5 min ago", current: false },
  { n: "v4", summary: "Picked Matched", who: "You · 9 min ago", current: false },
  { n: "v1", summary: "First cuts generated", who: "Agent · 18 min ago", current: false },
];

export const transcript = [
  { t: "00:00.00", scenic: "Scenic · 3.2 s", text: "Road through green hills, car window down. Natural sound only." },
  {
    t: "00:03.20",
    source: "IMG_2031",
    words: ["Okay", "so", "um", "day", "one.", "We", "left", "at", "six", "and", "it's", "been", "gravel."],
    struck: [2, 10],
  },
  { t: "00:14.90", scenic: "Scenic · 2.4 s", text: "Dust behind the car on a gravel road." },
  {
    t: "01:08.10",
    source: "IMG_2047",
    words: ["So", "this", "is", "camp.", "We", "got", "here", "just", "as", "the", "light", "was", "going,", "which,", "I", "mean,", "honestly", "we", "were", "kind", "of", "lucky.", "The", "tent", "is", "up,", "sort", "of."],
    struck: [25, 26],
    playhead: 4,
  },
  { t: "01:21.40", scenic: "Scenic · 4.1 s", text: "Waves breaking at dusk, wide shot." },
  { t: "01:25.50", source: "IMG_2049", words: ["Dinner", "is", "pasta", "again.", "Tomorrow", "the", "ridge", "if", "the", "wind", "drops."], struck: [] },
];

export const jobs = [
  {
    title: "Analysing footage · 30 clips",
    percent: "72%",
    left: "about 3 min left",
    step: "Transcribing clip 21 of 30 · 7:20 elapsed",
    stages: [
      { name: "Proxies", done: 1, label: "31:40 of 31:40 footage" },
      { name: "Shot detection", done: 1, label: "31:40 of 31:40 footage" },
      { name: "Transcription", done: 0.72, label: "11:32 of 16:05 speech", live: true },
      { name: "Captions and search", done: 0.43, label: "412 of 960 keyframes", live: true },
    ],
  },
  {
    title: "Generating cuts",
    percent: "58%",
    left: "about 5 min left",
    step: "Section 4 of 5 · Revision 1 of up to 4 · Local · Qwen 2.5 7B",
    note: "Revising: 3 shots need a second look. Estimate went from about 4 min to about 5 min.",
    segments: ["Outline", "Section 1", "Section 2", "Section 3", "Section 4", "Section 5", "Tight", "Relaxed"],
    current: 4,
  },
];
