"""W37: one bounded replacement of failed, independent proposal worker lanes.

A failed OS worker does not invalidate successful siblings. A failed lane may
take one *different, pre-approved* backlog task, never retry forever or invent
new work. No task execution outside an injected trusted worker driver.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

MAX_LANES = 3


def _eligible(task):
    return (isinstance(task, dict)
            and isinstance(task.get("id"), str)
            and task.get("kind") == "AUTO_PROPOSAL"
            and task.get("approval_required") is False)


def execute_lanes(primary, models, alternatives, *, spawn, collect,
                  on_success=None, on_failure=None):
    """Return completed lane records after at most one fresh task per failure.

    All initial workers are created before any waits; all complete/timeout
    independently. Successes are retained. Only failed slots may receive one
    DIFFERENT eligible task. All receipts require caller identity validation.
    """
    lane_count = len(primary)
    if (not 1 <= lane_count <= MAX_LANES or len(models) != lane_count
            or len(set(models)) != lane_count
            or not all(_eligible(task) for task in primary)
            or len({t["id"] for t in primary}) != lane_count
            or not isinstance(alternatives, list)
            or len(alternatives) > 100
            or not all(_eligible(task) for task in alternatives)
            or len({t["id"] for t in primary + alternatives})
            != len(primary) + len(alternatives)):
        raise ValueError("Only distinct approved proposal tasks and models permitted")
    active = [(i, primary[i], models[i], spawn(primary[i], models[i], i, 0))
              for i in range(lane_count)]
    completed = {}
    failures = []
    with ThreadPoolExecutor(max_workers=MAX_LANES) as pool:
        future_list = [(lane, task, model, proc,
                        pool.submit(collect, proc))
                       for lane, task, model, proc in active]
        for lane, task, model, proc, future in future_list:
            try:
                item = future.result()
                if on_success is not None:
                    on_success(task, model, proc, item)
            except Exception:
                # Nothing from child stderr or model error is printed publicly.
                if on_failure is not None:
                    on_failure(task, model, proc)
                failures.append(lane)
            else:
                completed[lane] = (task, model, proc, item)
    if len(failures) > len(alternatives):
        # In particular the ordinary W27 backlog has exactly three AUTO
        # tasks: no different successor exists. Fail closed rather than
        # looping the same dead task or claiming 3/3 success.
        raise ValueError("No distinct authorized next task for failed worker")
    recovered = []
    replacement = []
    for lane, task in zip(failures, alternatives):
        model = models[lane]
        replacement.append((lane, task, model, spawn(task, model, lane, 1)))
        recovered.append({"failed_task_id": primary[lane]["id"],
                          "replacement_task_id": task["id"]})
    if replacement:
        with ThreadPoolExecutor(max_workers=len(replacement)) as pool:
            future_list = [(lane, task, model, proc,
                            pool.submit(collect, proc))
                           for lane, task, model, proc in replacement]
            for lane, task, model, proc, future in future_list:
                try:
                    item = future.result()
                    if on_success is not None:
                        on_success(task, model, proc, item)
                except Exception:
                    if on_failure is not None:
                        on_failure(task, model, proc)
                    raise ValueError("Replacement worker failed (no infinite retries)") from None
                completed[lane] = (task, model, proc, item)
    if set(completed) != set(range(lane_count)):
        raise ValueError("Partial worker results; cannot claim three successes")
    return [completed[i] for i in range(lane_count)], recovered
