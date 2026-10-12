import { useEffect } from "react";
import { AgentColumn } from "./AgentColumn";
import { Bottom } from "./Bottom";
import { Centre } from "./Centre";
import { ClipList } from "./ClipList";
import { Overlays } from "./Overlays";
import { TopBar } from "./TopBar";
import { useEditor, type ScreenId } from "../store";

export function Workspace({ screen }: { screen: ScreenId }) {
  const theme = useEditor((state) => state.theme);
  const setScreen = useEditor((state) => state.setScreen);
  const setOverlay = useEditor((state) => state.setOverlay);
  const current = useEditor((state) => state.screen);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (screen !== current) setScreen(screen);
  }, [screen, current, setScreen]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
      if (event.key === "Escape") setOverlay(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOverlay]);

  return (
    <div className="relative flex h-full flex-col bg-page text-ink">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <ClipList />
        <main className="flex min-w-0 flex-1 flex-col bg-well">
          <Centre />
        </main>
        <AgentColumn />
      </div>
      <Bottom />
      <Overlays />
    </div>
  );
}
