import sys


def emit(message: str, prefix: str = "orchestrator", agent_id: str | None = None, out=None) -> None:
    if out is None:
        out = sys.stdout

    if agent_id is not None:
        label = f"[{prefix}:{agent_id}]"
    else:
        label = f"[{prefix}]"

    print(f"{label} {message}", file=out)


def orchestrator(message: str, out=None) -> None:
    emit(message, prefix="orchestrator", out=out)


def agent(agent_id: str, message: str, out=None) -> None:
    emit(message, prefix="agent", agent_id=agent_id, out=out)


def milestone(event: str, message: str, out=None) -> None:
    emit(message, prefix="milestone", agent_id=event, out=out)
