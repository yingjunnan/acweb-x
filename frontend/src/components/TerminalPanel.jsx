import { useEffect, useMemo, useRef } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";

export default function TerminalPanel({
  task,
  events,
  onStopTask,
  onSendInput,
  onResizeTerminal,
  replayCutoffSeq,
  socketState,
}) {
  const hostRef = useRef(null);
  const terminalRef = useRef(null);
  const fitAddonRef = useRef(null);
  const terminalDisposableRef = useRef(null);
  const resizeDisposableRef = useRef(null);
  const resizeObserverRef = useRef(null);
  const fitRafRef = useRef(0);
  const disposeTimerRef = useRef(0);
  const lastSeqRef = useRef(0);
  const currentTaskIdRef = useRef(null);
  const replayGuardRef = useRef(0);
  const onSendInputRef = useRef(onSendInput);
  const onResizeTerminalRef = useRef(onResizeTerminal);

  const writable = useMemo(() => Boolean(task && task.state === "running"), [task]);

  const syncSizeToBackend = () => {
    const terminal = terminalRef.current;
    if (!terminal || !currentTaskIdRef.current) {
      return;
    }

    if (terminal.cols > 0 && terminal.rows > 0) {
      onResizeTerminalRef.current?.(terminal.cols, terminal.rows);
    }
  };

  const safeFit = () => {
    const terminal = terminalRef.current;
    const fitAddon = fitAddonRef.current;
    const host = hostRef.current;

    if (!terminal || !fitAddon || !host || !host.isConnected) {
      return false;
    }

    try {
      fitAddon.fit();
    } catch {
      return false;
    }

    return terminal.cols > 0 && terminal.rows > 0;
  };

  const scheduleFit = (shouldSyncBackend = false) => {
    if (fitRafRef.current) {
      window.cancelAnimationFrame(fitRafRef.current);
    }

    fitRafRef.current = window.requestAnimationFrame(() => {
      fitRafRef.current = 0;
      if (safeFit() && shouldSyncBackend) {
        syncSizeToBackend();
      }
    });
  };

  useEffect(() => {
    onSendInputRef.current = onSendInput;
  }, [onSendInput]);

  useEffect(() => {
    onResizeTerminalRef.current = onResizeTerminal;
  }, [onResizeTerminal]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return undefined;
    }

    if (disposeTimerRef.current) {
      window.clearTimeout(disposeTimerRef.current);
      disposeTimerRef.current = 0;
    }

    let terminal = terminalRef.current;
    let fitAddon = fitAddonRef.current;

    if (!terminal || !fitAddon) {
      terminal = new Terminal({
        convertEol: false,
        cursorBlink: true,
        cursorStyle: "bar",
        fontFamily: '"JetBrains Mono", "SFMono-Regular", monospace',
        fontSize: 12,
        lineHeight: 1.45,
        scrollback: 5000,
        theme: {
          background: "#070d1f",
          foreground: "#d8e2ff",
          cursor: "#7cffde",
        },
      });

      fitAddon = new FitAddon();
      terminal.loadAddon(fitAddon);
      terminal.open(host);

      terminalRef.current = terminal;
      fitAddonRef.current = fitAddon;
    }

    terminalDisposableRef.current?.dispose();
    resizeDisposableRef.current?.dispose();

    terminalDisposableRef.current = terminal.onData((data) => {
      if (!currentTaskIdRef.current) {
        return;
      }
      if (replayGuardRef.current > 0) {
        return;
      }
      onSendInputRef.current(data);
    });

    resizeDisposableRef.current = terminal.onResize(({ cols, rows }) => {
      if (!currentTaskIdRef.current) {
        return;
      }
      onResizeTerminalRef.current?.(cols, rows);
    });

    const observer = new ResizeObserver(() => {
      scheduleFit(true);
    });
    observer.observe(host);
    resizeObserverRef.current = observer;

    const handleMouseDown = () => {
      terminal.focus();
    };
    host.addEventListener("mousedown", handleMouseDown);

    scheduleFit(true);
    terminal.focus();

    return () => {
      host.removeEventListener("mousedown", handleMouseDown);
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;

      terminalDisposableRef.current?.dispose();
      terminalDisposableRef.current = null;
      resizeDisposableRef.current?.dispose();
      resizeDisposableRef.current = null;

      if (fitRafRef.current) {
        window.cancelAnimationFrame(fitRafRef.current);
        fitRafRef.current = 0;
      }

      const terminalToDispose = terminalRef.current;
      const fitAddonToDispose = fitAddonRef.current;

      disposeTimerRef.current = window.setTimeout(() => {
        disposeTimerRef.current = 0;

        if (terminalRef.current === terminalToDispose) {
          terminalToDispose?.dispose();
          terminalRef.current = null;
        }

        if (fitAddonRef.current === fitAddonToDispose) {
          fitAddonRef.current = null;
        }
      }, 80);
    };
  }, []);

  useEffect(() => {
    const terminal = terminalRef.current;
    if (!terminal) {
      return;
    }

    if (currentTaskIdRef.current !== (task?.id ?? null)) {
      currentTaskIdRef.current = task?.id ?? null;
      lastSeqRef.current = 0;
      replayGuardRef.current = 0;
      terminal.clear();

      if (!task) {
        terminal.writeln("Select a task to attach");
        return;
      }

      scheduleFit(true);
      terminal.focus();
    }
  }, [task]);

  useEffect(() => {
    const terminal = terminalRef.current;
    if (!terminal) {
      return;
    }

    for (const event of events) {
      if (event.seq <= lastSeqRef.current) {
        continue;
      }

      if (event.seq <= replayCutoffSeq) {
        replayGuardRef.current += 1;
        terminal.write(event.data, () => {
          replayGuardRef.current = Math.max(0, replayGuardRef.current - 1);
        });
      } else {
        terminal.write(event.data);
      }

      lastSeqRef.current = event.seq;
    }
  }, [events, replayCutoffSeq]);

  useEffect(() => {
    scheduleFit(true);
  }, [socketState]);

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

      <div className="terminal-output" ref={hostRef} />

      <div className="terminal-status">
        <span className={`status-dot status-${socketState}`} />
        <span>Socket: {socketState}</span>
        <span>{writable ? "Input enabled" : "Input disabled"}</span>
      </div>
    </section>
  );
}
