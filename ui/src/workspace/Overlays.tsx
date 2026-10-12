import { jobs, versions } from "./fixtures";
import { useEditor } from "../store";

export function Overlays() {
  const overlay = useEditor((state) => state.overlay);
  const setOverlay = useEditor((state) => state.setOverlay);
  const setScreen = useEditor((state) => state.setScreen);
  if (!overlay) return null;
  if (overlay === "export") {
    return (
      <>
        <div className="absolute inset-0 z-20 bg-black/40" onClick={() => setOverlay(null)} />
        <aside className="sheet-in absolute bottom-16 right-4 top-16 z-30 w-[380px] overflow-auto rounded-xl bg-page p-5 shadow-sheet" onClick={(event) => event.stopPropagation()}>
          <ExportSheet onClose={() => setOverlay(null)} />
        </aside>
        <div className="toast-in absolute bottom-4 left-4 z-30 w-80 space-y-2">
          <div className="rounded-lg bg-raised p-3 text-sm shadow-sheet">
            <div className="flex justify-between">
              <span>Exporting Matched v7</span>
              <span>42%</span>
            </div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-line">
              <span className="block h-full w-[42%] bg-agent" />
            </div>
            <p className="mt-2 text-muted">Frame 4,860 of 11,580 · about 2 min left</p>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-raised p-3 text-sm shadow-sheet">
            <span>
              <span className="text-agent">Exported</span> Tight v3
              <span className="block text-muted">MP4 + FCPXML · 5:48 · 812 MB</span>
            </span>
            <button type="button" className="rounded-md bg-page px-2 py-1">
              Show in folder
            </button>
          </div>
        </div>
      </>
    );
  }
  return (
    <div className="absolute inset-0 z-20 grid place-items-center bg-black/50" onClick={() => setOverlay(null)}>
      <div className="overlay max-h-[90%] w-[min(720px,92%)] overflow-auto rounded-xl bg-page p-5 shadow-sheet" onClick={(event) => event.stopPropagation()}>
        {overlay === "jobs" ? <Jobs onClose={() => setOverlay(null)} /> : null}
        {overlay === "cloud" ? (
          <Cloud
            onLocal={() => setOverlay(null)}
            onCloud={() => {
              setOverlay(null);
              setScreen("generate");
            }}
          />
        ) : null}
        {overlay === "cloud-failed" ? <CloudFailed onLocal={() => setScreen("generate")} onRetry={() => setOverlay("cloud")} /> : null}
        {overlay === "versions" ? <Versions onClose={() => setOverlay(null)} /> : null}
      </div>
    </div>
  );
}

function Jobs({ onClose }: { onClose: () => void }) {
  return (
    <>
      <header className="flex items-center justify-between">
        <h2 className="text-lg">Jobs</h2>
        <button type="button" className="text-sm text-muted" onClick={onClose}>
          Close Esc
        </button>
      </header>
      <div className="mt-4 space-y-3">
        {jobs.map((job) => (
          <article key={job.title} className="rounded-lg bg-raised p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">{job.title}</p>
                <p className="text-sm text-muted">{job.step}</p>
              </div>
              <p className="text-sm">
                {job.percent} {job.left}
              </p>
            </div>
            {job.note ? <p className="mt-2 rounded-md bg-[#3a2e1c] px-3 py-2 text-sm text-scenic">{job.note}</p> : null}
            {job.segments ? (
              <div className="mt-3 flex h-2 gap-0.5">
                {job.segments.map((name, index) => (
                  <span key={name} className={`h-full flex-1 rounded-sm ${index === job.current ? "bg-agent" : index < (job.current ?? 0) ? "bg-muted" : "bg-line"}`} title={name} />
                ))}
              </div>
            ) : null}
            {job.stages ? (
              <ul className="mt-3 space-y-2 text-sm">
                {job.stages.map((stage) => (
                  <li key={stage.name} className="grid grid-cols-[9rem_1fr_auto] items-center gap-2">
                    <span>{stage.name}</span>
                    <span className="h-1.5 overflow-hidden rounded-full bg-line">
                      <span className={`block h-full ${stage.live ? "bg-agent" : "bg-muted"}`} style={{ width: `${stage.done * 100}%` }} />
                    </span>
                    <span className="text-muted">{stage.label}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-3 flex justify-end gap-2">
              <button type="button" className="rounded-md bg-page px-3 py-1">
                Pause
              </button>
              <button type="button" className="px-3 py-1 text-muted">
                Cancel
              </button>
            </div>
          </article>
        ))}
        <article className="rounded-lg p-3 outline outline-1 outline-danger">
          <p>
            <span className="mr-2 rounded-full bg-danger/20 px-2 py-0.5 text-xs text-danger">Failed</span>
            GOPR0193.MP4 couldn't be analysed
          </p>
          <p className="mt-1 text-sm text-muted">Unsupported codec (HEVC 10-bit). Convert to H.264, then retry. The cut is being made without it.</p>
          <div className="mt-3 flex gap-2">
            <button type="button" className="rounded-md bg-raised px-3 py-1">
              Retry
            </button>
            <button type="button" className="px-3 py-1 text-muted">
              Exclude clip
            </button>
          </div>
        </article>
      </div>
      <p className="mt-4 text-xs text-muted">Jobs keep their place if the app restarts and resume from the last finished step.</p>
    </>
  );
}

function Cloud({ onLocal, onCloud }: { onLocal: () => void; onCloud: () => void }) {
  return (
    <>
      <h2 className="text-lg">Use the cloud for this run?</h2>
      <p className="mt-1 text-sm text-muted">Anthropic · Claude. Your default stays local.</p>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-raised p-3">
          <p className="text-xs text-muted">Estimated time</p>
          <p className="text-lg">about 3 min</p>
          <p className="text-sm text-muted">Local would take about 9 min</p>
        </div>
        <div className="rounded-lg bg-raised p-3">
          <p className="text-xs text-muted">Estimated cost</p>
          <p className="text-lg">about $0.14</p>
          <p className="text-sm text-muted">~18k tokens in · ~6k out, 3 variants</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-xs tracking-wide text-muted">WHAT WILL BE SENT</p>
          <ul className="mt-2 space-y-1">
            <li>Transcripts</li>
            <li>Shot descriptions</li>
            <li>Timing and quality stats</li>
          </ul>
        </div>
        <div>
          <p className="text-xs tracking-wide text-muted">NEVER LEAVES THIS MAC</p>
          <ul className="mt-2 space-y-1">
            <li>Video and audio</li>
            <li>Keyframes and thumbnails</li>
            <li>File names and folders</li>
          </ul>
        </div>
      </div>
      <p className="mt-4 text-sm text-muted">If a cloud call fails, the run pauses and you can retry or finish on the local model.</p>
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" className="press rounded-md bg-raised px-3 py-2" onClick={onLocal}>
          Keep it local
        </button>
        <button type="button" className="press rounded-md bg-paper px-3 py-2 text-page" onClick={onCloud}>
          Generate cuts on cloud
        </button>
      </div>
    </>
  );
}

function CloudFailed({ onLocal, onRetry }: { onLocal: () => void; onRetry: () => void }) {
  return (
    <div className="rounded-lg p-1 outline outline-1 outline-danger">
      <h2 className="text-lg">Cloud call failed in Section 3. Generation is paused.</h2>
      <p className="mt-2 text-sm text-muted">The service didn't respond after 3 tries. Sections 1 and 2 are kept.</p>
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" className="press rounded-md bg-raised px-3 py-2" onClick={onRetry}>
          Retry cloud
        </button>
        <button type="button" className="press rounded-md bg-paper px-3 py-2 text-page" onClick={onLocal}>
          Continue on local model
        </button>
      </div>
    </div>
  );
}

function ExportSheet({ onClose }: { onClose: () => void }) {
  return (
    <>
      <h2 className="text-lg">Export video</h2>
      <p className="text-sm text-muted">Matched · v8 · 7:43 · 72 cuts</p>
      <p className="mt-4 text-xs tracking-wide text-muted">PRESET</p>
      <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
        <button type="button" className="rounded-lg p-3 text-left outline outline-1 outline-paper">
          <span className="block font-medium">1080p</span>
          <span className="text-muted">H.264 · for sharing</span>
          <span className="block text-muted">about 1.1 GB</span>
        </button>
        <button type="button" className="rounded-lg bg-raised p-3 text-left">
          <span className="block font-medium">4K master</span>
          <span className="text-muted">ProRes 422 · about 38 GB</span>
        </button>
        <button type="button" className="rounded-lg bg-raised p-3 text-left">
          <span className="block font-medium">720p review</span>
          <span className="text-muted">H.264 · small · about 300 MB</span>
        </button>
      </div>
      <p className="mt-4 text-xs tracking-wide text-muted">SAVE TO</p>
      <p className="mt-1 rounded-md bg-raised px-3 py-2">~/Movies/Rough Cuts/Wild Coast road trip – Matched v8.mp4</p>
      <p className="mt-4 text-xs tracking-wide text-muted">ALSO EXPORT A TIMELINE FILE</p>
      <ul className="mt-2 space-y-2 text-sm">
        <li>DaVinci Resolve and Final Cut Pro · FCPXML</li>
        <li className="text-muted">Premiere Pro · XML</li>
        <li className="text-muted">OpenTimelineIO · .otio</li>
      </ul>
      <div className="mt-4 flex items-center justify-end gap-3">
        <span className="text-sm text-muted">Runs in the background · about 4 min on this Mac</span>
        <button type="button" className="text-sm" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="press rounded-md bg-paper px-3 py-2 text-page" onClick={onClose}>
          Export video
        </button>
      </div>
    </>
  );
}

function Versions({ onClose }: { onClose: () => void }) {
  return (
    <>
      <header className="flex justify-between">
        <h2 className="text-lg">Versions</h2>
        <button type="button" className="text-sm text-muted" onClick={onClose}>
          Close
        </button>
      </header>
      <ul className="mt-3 divide-y divide-line">
        {versions.map((version) => (
          <li key={version.n} className="flex items-center gap-3 py-2">
            <span className="w-8">{version.n}</span>
            <span className="flex-1">
              <span className="block">{version.summary}</span>
              <span className="text-xs text-muted">{version.who}</span>
            </span>
            <button type="button" className="text-sm text-talking">
              {version.current ? "Compare" : "Restore"}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
