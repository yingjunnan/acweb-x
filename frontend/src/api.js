const headers = {
  "Content-Type": "application/json",
};

async function parseJson(response) {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchProjects() {
  const response = await fetch("/api/v1/projects");
  return parseJson(response);
}

export async function fetchTasks() {
  const response = await fetch("/api/v1/tasks");
  return parseJson(response);
}

export async function createTask(command, cwd) {
  const response = await fetch("/api/v1/tasks", {
    method: "POST",
    headers,
    body: JSON.stringify({ command, cwd }),
  });
  return parseJson(response);
}

export async function stopTask(taskId) {
  const response = await fetch(`/api/v1/tasks/${taskId}/stop`, {
    method: "POST",
  });
  return parseJson(response);
}

export async function fetchTaskEvents(taskId, fromSeq = 1) {
  const response = await fetch(`/api/v1/tasks/${taskId}/events?from_seq=${fromSeq}`);
  return parseJson(response);
}
