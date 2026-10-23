from typing import Literal

TaskStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]
ACTIVE = ("queued", "running")
TRANSITIONS = {"queued": {"running", "canceled", "failed"},
               "running": {"succeeded", "failed", "canceled"}}


def transition(current: str, target: str) -> str:
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid task transition: {current} -> {target}")
    return target
