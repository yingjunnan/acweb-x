function renderTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

function canDelete(task) {
  return task.state !== "running" && task.state !== "queued";
}

export default function TaskSidebar({ tasks, selectedTaskId, onSelectTask, onDeleteTask }) {
  return (
    <aside className="panel sidebar">
      <div className="panel-title">Tasks</div>
      <div className="task-list">
        {tasks.length === 0 && <p className="empty-state">No tasks yet</p>}
        {tasks.map((task) => {
          const active = selectedTaskId === task.id;
          const deletable = canDelete(task);

          return (
            <div key={task.id} className={`task-item ${active ? "active" : ""}`}>
              <button type="button" className="task-select" onClick={() => onSelectTask(task.id)}>
                <div className="task-item-top">
                  <span className={`badge state-${task.state}`}>{task.state}</span>
                  <span className="task-id">{task.id.slice(0, 8)}</span>
                </div>
                <div className="task-command">{task.command}</div>
                <div className="task-time">{renderTime(task.created_at)}</div>
              </button>

              <button
                type="button"
                className="task-delete"
                title={deletable ? "Delete task record" : "Stop task before deleting"}
                disabled={!deletable}
                onClick={() => onDeleteTask(task.id)}
              >
                Del
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
