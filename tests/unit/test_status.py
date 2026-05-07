import io

from scripts.status import agent, emit, milestone, orchestrator


def test_orchestrator_format():
    out = io.StringIO()
    orchestrator("starting research", out=out)
    assert out.getvalue() == "[orchestrator] starting research\n"


def test_agent_format():
    out = io.StringIO()
    agent("item-a", "fetching results", out=out)
    assert out.getvalue() == "[agent:item-a] fetching results\n"


def test_milestone_format():
    out = io.StringIO()
    milestone("round_complete", "round 1 done", out=out)
    assert out.getvalue() == "[milestone:round_complete] round 1 done\n"


def test_emit_custom_prefix():
    out = io.StringIO()
    emit("hello", prefix="custom", out=out)
    assert out.getvalue() == "[custom] hello\n"


def test_emit_custom_prefix_with_agent_id():
    out = io.StringIO()
    emit("hello", prefix="custom", agent_id="x1", out=out)
    assert out.getvalue() == "[custom:x1] hello\n"


def test_all_functions_write_to_provided_stream():
    streams = [io.StringIO(), io.StringIO(), io.StringIO(), io.StringIO()]
    orchestrator("msg", out=streams[0])
    agent("a", "msg", out=streams[1])
    milestone("ev", "msg", out=streams[2])
    emit("msg", out=streams[3])

    for stream in streams:
        assert stream.getvalue() != ""
