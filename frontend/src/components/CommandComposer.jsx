import { useState } from "react";

export default function CommandComposer({ onSubmit, busy, defaultCwd }) {
  const [command, setCommand] = useState("zsh -i");
  const [cwd, setCwd] = useState(defaultCwd || "");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!command.trim()) {
      return;
    }
    await onSubmit(command.trim(), cwd.trim() || null);
  }

  return (
    <form className="panel composer" onSubmit={handleSubmit}>
      <div className="panel-title">Launch CLI Task</div>
      <label className="field">
        <span>Command</span>
        <input
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="zsh -i"
        />
      </label>
      <label className="field">
        <span>Working Directory (optional)</span>
        <input
          value={cwd}
          onChange={(event) => setCwd(event.target.value)}
          placeholder="/Users/yingjunnan/workspace"
        />
      </label>
      <button className="btn-primary" disabled={busy} type="submit">
        {busy ? "Starting..." : "Start Task"}
      </button>
    </form>
  );
}
