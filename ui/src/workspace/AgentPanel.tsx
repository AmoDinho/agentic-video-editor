export function AgentPanel({ empty }: { empty: boolean }) {
  return (
    <aside className="flex w-[23%] min-w-[260px] flex-col border-l border-line">
      <header className="flex items-center justify-between border-b border-line px-4 py-3 text-sm">
        <span>Agent</span>
        <span className="text-muted">Local · Qwen 2.5 7B</span>
      </header>
      <div className="flex-1 overflow-auto px-4 py-4 text-sm">
        {empty ? (
          <>
            <p>The agent starts as soon as you choose a style. Here is what happens:</p>
            <ol className="mt-4 space-y-3">
              {[
                ["Drop footage.", "Each clip is analysed in shooting order."],
                ["Choose a style.", "A reference video or a saved style."],
                ["Generate cuts.", "Three variants: tight, matched, relaxed."],
                ["Refine and export.", "Ask, edit the transcript, or trim the timeline."],
              ].map(([title, body], index) => (
                <li key={title} className="flex gap-3">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-raised text-muted">{index + 1}</span>
                  <span>
                    <span className="font-medium">{title}</span> <span className="text-muted">{body}</span>
                  </span>
                </li>
              ))}
            </ol>
          </>
        ) : (
          <p className="text-muted">Waiting for you to generate.</p>
        )}
      </div>
      <form className="border-t border-line p-3" onSubmit={(event) => event.preventDefault()}>
        <input
          className="w-full rounded-md border border-line bg-well px-3 py-2 text-sm"
          placeholder="Ask for a change"
          aria-label="Ask for a change"
        />
      </form>
    </aside>
  );
}
