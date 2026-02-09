import { useMemo } from "react";

function renderTimestamp(ts) {
  return new Date(ts).toLocaleTimeString();
}

export default function TerminalPanel({ task, events, onStopTask }) {
  const lines = useMemo(() => {
    return events.map((event) => {
      const stream = event.stream === "system" ? "SYS" : event.stream.toUpperCase();
      return `[${renderTimestamp(event.ts)}] ${stream} ${event.data}`;
    });
  }, [events]);

  return (
    <section className="panel terminal-panel">
      <div className="terminal-header">
        <div>
          <div className="panel-title">Live Output</div>
          {task ? (
            <div className="terminal-meta">
              <span className={`badge state-${task.state}`}>{task.state}</span>
              <span>{task.command}</span>
            </div>
          ) : (
            <div className="terminal-meta">Select a task to attach</div>
          )}
        </div>
        {task && (
          <button
            className="btn-danger"
            type="button"
            disabled={task.state !== "running" && task.state !== "queued"}
            onClick={() => onStopTask(task.id)}
          >
            Stop Task
          </button>
        )}
      </div>
      <pre className="terminal-output">{lines.length ? lines.join("") : "No output yet."}</pre>
    </section>
  );
}
