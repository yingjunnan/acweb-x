import { useMemo, useState } from "react";

function renderTimestamp(ts) {
  return new Date(ts).toLocaleTimeString();
}

export default function TerminalPanel({ task, events, onStopTask, onSendInput }) {
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);

  const lines = useMemo(() => {
    return events.map((event) => {
      const stream = event.stream === "system" ? "SYS" : event.stream.toUpperCase();
      return `[${renderTimestamp(event.ts)}] ${stream} ${event.data}`;
    });
  }, [events]);

  const writable = Boolean(task && (task.state === "running" || task.state === "queued"));

  async function handleSend(event) {
    event.preventDefault();
    if (!writable || !inputValue.trim()) {
      return;
    }

    const payload = inputValue.endsWith("\n") ? inputValue : `${inputValue}\n`;

    setSending(true);
    try {
      await onSendInput(payload);
      setInputValue("");
    } finally {
      setSending(false);
    }
  }

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

      <form className="terminal-input" onSubmit={handleSend}>
        <input
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder={writable ? "Type command input and send" : "Task is not writable"}
          disabled={!writable || sending}
        />
        <button className="btn-primary terminal-send" type="submit" disabled={!writable || sending || !inputValue.trim()}>
          {sending ? "Sending..." : "Send Input"}
        </button>
      </form>
    </section>
  );
}
