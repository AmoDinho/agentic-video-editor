import { AbsoluteFill, OffthreadVideo, Sequence, useVideoConfig } from "remotion";

export type CutSegment = {
  id: string;
  src: string;
  inFrame: number;
  durationInFrames: number;
  role: "a_roll" | "b_roll";
};

export type CutProps = {
  segments: CutSegment[];
};

export const CutComposition: React.FC<CutProps> = ({ segments }) => {
  const { fps } = useVideoConfig();
  let cursor = 0;
  return (
    <AbsoluteFill style={{ background: "#0f1012" }}>
      {segments.map((segment) => {
        const from = cursor;
        cursor += segment.durationInFrames;
        return (
          <Sequence key={segment.id} from={from} durationInFrames={segment.durationInFrames} name={segment.id}>
            <OffthreadVideo
              src={segment.src}
              startFrom={segment.inFrame}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          </Sequence>
        );
      })}
      {segments.length === 0 ? (
        <AbsoluteFill
          style={{
            color: "#9a9a94",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "IBM Plex Sans, sans-serif",
            fontSize: 28,
          }}
        >
          Your cut will appear here
        </AbsoluteFill>
      ) : null}
      <span hidden>{fps}</span>
    </AbsoluteFill>
  );
};

export function cutDuration(segments: CutSegment[]): number {
  return segments.reduce((sum, segment) => sum + segment.durationInFrames, 0);
}
