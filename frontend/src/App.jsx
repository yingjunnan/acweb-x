import { useEffect, useMemo, useRef, useState } from "react";
import CommandComposer from "./components/CommandComposer";
import TaskSidebar from "./components/TaskSidebar";
import TerminalPanel from "./components/TerminalPanel";
import { createTask, fetchProjects, fetchTaskEvents, fetchTasks, stopTask } from "./api";

function normalizeEvents(input) {
  return [...input].sort((a, b) => a.seq - b.seq);
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const wsRef = useRef(null);

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
      return undefined;
    }

    let closed = false;

    async function openSocket() {
      try {
        const history = await fetchTaskEvents(selectedTaskId, 1);
        if (closed) {
          return;
        }
        setEvents(normalizeEvents(history.items));
      } catch (err) {
        setError(err.message);
      }

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}/ws/tasks/${selectedTaskId}`);
      wsRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "attached") {
            const snapshot = payload.snapshot || [];
            setEvents((prev) => normalizeEvents([...prev, ...snapshot]));
            return;
          }
          if (payload.type === "output") {
            const next = payload.event;
            setEvents((prev) => {
              if (prev.some((item) => item.seq === next.seq)) {
                return prev;
              }
              return [...prev, next];
            });
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
        if (!closed) {
          setTimeout(() => {
            if (!closed) {
              openSocket();
            }
          }, 1200);
        }
      };
    }

    openSocket();

    return () => {
      closed = true;
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>acweb</h1>
          <p>CLI control plane for long-running terminal workloads</p>
        </div>
        <div className="project-chip">
          Project: {projects[0]?.name || "Loading..."}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="layout">
        <TaskSidebar tasks={tasks} selectedTaskId={selectedTaskId} onSelectTask={setSelectedTaskId} />
        <section className="workspace">
          <CommandComposer
            onSubmit={handleCreateTask}
            busy={busy}
            defaultCwd={projects[0]?.path}
          />
          <TerminalPanel task={selectedTask} events={events} onStopTask={handleStopTask} />
        </section>
      </main>
    </div>
  );
}
