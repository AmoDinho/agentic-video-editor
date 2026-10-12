import type { Cut, Segment } from "../store";

const reasons = [
  "Steadiest wide shot. Length matches the 2–5 s scenic shots in the style.",
  "Clearest sentence, cut on the pause so no word is clipped.",
  "Keeps the drive-in opening without the shaky handheld.",
];

function segment(index: number, role: Segment["role"], start: number, length: number, section: string): Segment {
  return {
    id: `s${index}`,
    source: role === "a_roll" ? `IMG_${2030 + index}.MOV` : `GOPR0${180 + index}.MP4`,
    in_s: 0,
    out_s: length,
    role,
    reason: reasons[index % reasons.length],
    locked: index === 4,
    section,
  };
}

const lengths = [8, 4, 6, 3, 5, 9, 4, 7, 3, 6, 8, 4];
const roles: Segment["role"][] = ["a_roll", "b_roll", "a_roll", "b_roll", "b_roll", "a_roll", "b_roll", "a_roll", "b_roll", "a_roll", "b_roll", "a_roll"];
const sections = ["1 · Drive in", "1 · Drive in", "1 · Drive in", "2 · Beach camp", "2 · Beach camp", "2 · Beach camp", "3 · Morning hike", "3 · Morning hike", "3 · Morning hike", "4 · Village", "4 · Village", "5 · Last campfire"];

let cursor = 0;
export const sampleSegments: Segment[] = lengths.map((length, index) => {
  const segmentStart = cursor;
  cursor += length;
  return { ...segment(index, roles[index], segmentStart, length, sections[index]), in_s: 1, out_s: 1 + length };
});

export const sampleCut: Cut = {
  id: "matched",
  name: "Matched",
  runtime_s: sampleSegments.reduce((sum, item) => sum + (item.out_s - item.in_s), 0),
  segments: sampleSegments,
};

export const sampleWords = [
  { start: 0, end: 3.2, text: "Road through green hills, car window down.", scenic: true },
  { start: 3.2, end: 14.9, text: "Okay so we left at six, and the last bit was gravel the whole way.", source: "IMG_2031" },
  { start: 14.9, end: 18, text: "Dust behind the car on a gravel road.", scenic: true },
];
