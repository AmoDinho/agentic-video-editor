import { Player, type PlayerRef } from "@remotion/player";
import { forwardRef } from "react";
import { CutComposition, cutDuration, type CutProps, type CutSegment } from "./CutComposition";

type Props = {
  segments: CutSegment[];
  fps?: number;
  width?: number;
  height?: number;
};

export const CutPlayer = forwardRef<PlayerRef, Props>(function CutPlayer(
  { segments, fps = 30, width = 1920, height = 1080 },
  ref,
) {
  const duration = Math.max(1, cutDuration(segments));
  return (
    <Player
      ref={ref}
      component={CutComposition}
      inputProps={{ segments } satisfies CutProps}
      durationInFrames={duration}
      compositionWidth={width}
      compositionHeight={height}
      fps={fps}
      acknowledgeRemotionLicense
      controls={false}
      style={{ width: "100%", height: "100%" }}
    />
  );
});
