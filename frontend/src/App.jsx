import { useEffect, useMemo, useRef, useState } from "react";
import CommandComposer from "./components/CommandComposer";
import TaskSidebar from "./components/TaskSidebar";
import TerminalPanel from "./components/TerminalPanel";
import { createTask, fetchProjects, fetchTaskEvents, fetchTasks, sendTaskInput, stopTask } from "./api";

function mergeEvents(previous, incoming) {
  const map = new Map();
  for (const event of previous) {
    map.set(event.seq, event);
  }
  for (const event of incoming) {
    map.set(event.seq, event);
  }
  return [...map.values()].sort((a, b) => a.seq - b.seq);
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const wsRef = useRef(null);
  const nextSeqRef = useRef(1);

  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) ?? null,
    [tasks, selectedTaskId]
  );

  useEffect(() => {
    async function bootstrap() {
      try {
        const [projectData, taskData] = await Promise.all([fetchProjects(), fetchTasks()]);
        setProjects(projectData);
        setTasks(taskData);
        if (taskData.length) {
          setSelectedTaskId(taskData[0].id);
        }
      } catch (err) {
        setError(err.message);
      }
    }

    bootstrap();
  }, []);

  useEffect(() => {
    if (!selectedTaskId) {
      setEvents([]);
      nextSeqRef.current = 1;
      return undefined;
    }

    let closed = false;
    let reconnectTimer = null;

    setEvents([]);
    nextSeqRef.current = 1;

    async function openSocket() {
      const fromSeq = nextSeqRef.current;

      try {
        const history = await fetchTaskEvents(selectedTaskId, fromSeq);
        if (closed) {
          return;
        }
        setEvents((prev) => mergeEvents(prev, history.items || []));
        nextSeqRef.current = history.next_seq || nextSeqRef.current;
      } catch (err) {
        if (!closed) {
          setError(err.message);
        }
      }

      if (closed) {
        return;
      }

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(
        `${protocol}://${window.location.host}/ws/tasks/${selectedTaskId}?from_seq=${nextSeqRef.current}`
      );
      wsRef.current = socket;

      socket.onopen = () => {
        setError("");
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "attached") {
            const snapshot = payload.snapshot || [];
            setEvents((prev) => mergeEvents(prev, snapshot));
            if (typeof payload.next_seq === "number") {
              nextSeqRef.current = payload.next_seq;
            }
            return;
          }

          if (payload.type === "output") {
            const nextEvent = payload.event;
            setEvents((prev) => mergeEvents(prev, [nextEvent]));
            if (typeof nextEvent?.seq === "number") {
              nextSeqRef.current = Math.max(nextSeqRef.current, nextEvent.seq + 1);
            }
            return;
          }

          if (payload.type === "error") {
            setError(payload.message || "Socket error");
          }
        } catch {
          setError("Invalid socket message");
        }
      };

      socket.onclose = () => {
        if (closed) {
          return;
        }
        reconnectTimer = window.setTimeout(() => {
          if (!closed) {
            openSocket();
          }
        }, 1200);
      };
    }

    openSocket();

    return () => {
      closed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [selectedTaskId]);

  async function refreshTasks(preferredTaskId = null) {
    const taskData = await fetchTasks();
    setTasks(taskData);
    if (preferredTaskId) {
      setSelectedTaskId(preferredTaskId);
    } else if (!taskData.find((task) => task.id === selectedTaskId)) {
      setSelectedTaskId(taskData[0]?.id || null);
    }
  }

  async function handleCreateTask(command, cwd) {
    setBusy(true);
    setError("");
    try {
      const response = await createTask(command, cwd);
      await refreshTasks(response.task.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleStopTask(taskId) {
    try {
      await stopTask(taskId);
      await refreshTasks(taskId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSendTaskInput(data) {
    if (!selectedTaskId) {
      return;
    }
    try {
      await sendTaskInput(selectedTaskId, data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>acweb</h1>
          <p>CLI control plane for long-running terminal workloads</p>
        </div>
        <div className="project-chip">Project: {projects[0]?.name || "Loading..."}</div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="layout">
        <TaskSidebar tasks={tasks} selectedTaskId={selectedTaskId} onSelectTask={setSelectedTaskId} />
        <section className="workspace">
          <CommandComposer onSubmit={handleCreateTask} busy={busy} defaultCwd={projects[0]?.path} />
          <TerminalPanel
            task={selectedTask}
            events={events}
            onStopTask={handleStopTask}
            onSendInput={handleSendTaskInput}
          />
        </section>
      </main>
    </div>
  );
}
