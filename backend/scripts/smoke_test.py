from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def get_json(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_health(timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            payload = get_json("/api/v1/health")
            if isinstance(payload, dict) and payload.get("status") == "ok":
                return
        except urllib.error.URLError:
            pass
        time.sleep(0.5)
    raise RuntimeError("backend health check timed out")


def main() -> None:
    wait_health()

    created = post_json("/api/v1/tasks", {"command": "echo smoke-test-ok"})
    task_id = created["task"]["id"]

    time.sleep(1)

    tasks = get_json("/api/v1/tasks")
    if not isinstance(tasks, list) or not any(task.get("id") == task_id for task in tasks):
        raise RuntimeError("created task not found in list")

    events_payload = get_json(f"/api/v1/tasks/{task_id}/events?from_seq=1")
    items = events_payload.get("items", []) if isinstance(events_payload, dict) else []
    if not any("smoke-test-ok" in item.get("data", "") for item in items):
        raise RuntimeError("expected stdout content not found in events")

    print("smoke_test_passed", task_id, len(items))


if __name__ == "__main__":
    main()
