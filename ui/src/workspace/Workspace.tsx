import { useEffect } from "react";
import { Player } from "@remotion/player";
import { CutComposition } from "../player/CutComposition";
import { clock, useEditor, type Cut } from "../store";
import { AgentPanel } from "./AgentPanel";
import { MediaBin } from "./MediaBin";
import { Timeline } from "./Timeline";
import { TopBar } from "./TopBar";

export function Workspace({ cut, empty = false }: { cut?: Cut; empty?: boolean }) {
  const { theme, playing, togglePlay, playhead, setPlayhead, select, selectedId } = useEditor();
  const segments = cut?.segments ?? [];
  const total = cut?.runtime_s ?? 0;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
      if (event.code === "Space") {
        event.preventDefault();
        togglePlay();
      } else if (event.key === "j" || event.key === "J") {
        setPlayhead(Math.max(0, playhead - 2));
      } else if (event.key === "l" && !event.metaKey) {
        setPlayhead(Math.min(total, playhead + 2));
      } else if (event.key === "k" || event.key === "K") {
        togglePlay();
      } else if ((event.key === "Delete" || event.key === "Backspace") && selectedId) {
        select(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [playhead, selectedId, setPlayhead, select, togglePlay, total]);

  return (
    <div className="flex h-full flex-col bg-page text-ink">
      <TopBar status={empty ? "Nothing running" : playing ? "Playing the cut" : "All changes saved"} remaining={empty ? "" : clock(total)} />
      <div className="flex min-h-0 flex-1">
        <MediaBin segments={segments} empty={empty} />
        <main className="flex min-w-0 flex-1 flex-col bg-well">
          {empty ? <DropZone /> : <PlayerWell total={total} />}
        </main>
        <AgentPanel empty={empty} />
      </div>
      <Timeline segments={segments} />
    </div>
  );
}

function DropZone() {
  return (
    <div className="m-6 grid flex-1 place-items-center rounded-xl border border-dashed border-line text-center">
      <div>
        <h1 className="text-xl">Drop a folder of clips to start</h1>
        <p className="mt-2 text-sm text-muted">Analysis starts the moment clips arrive. Your source files are never changed.</p>
      </div>
    </div>
  );
}

function PlayerWell({ total }: { total: number }) {
  const playhead = useEditor((state) => state.playhead);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid min-h-0 flex-1 place-items-center">
        <Player
          component={CutComposition}
          inputProps={{ segments: [] }}
          durationInFrames={Math.max(1, Math.round(total * 30))}
          compositionWidth={1920}
          compositionHeight={1080}
          fps={30}
          acknowledgeRemotionLicense
          controls={false}
          style={{ width: "100%", maxHeight: "100%", aspectRatio: "16 / 9" }}
        />
      </div>
      <div className="flex items-center gap-3 px-4 py-2 text-sm">
        <span>
          {clock(playhead)} / {clock(total)}
        </span>
        <span className="text-muted">Plays straight from the cut. No render needed.</span>
      </div>
    </div>
  );
}
