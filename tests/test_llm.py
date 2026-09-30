"""The tool loop against a fake Claude client. No network, no key."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from core import llm
from tests.conftest import make_config


def _text(t):
    return NS(type="text", text=t)


def _tool_use(id_, name, **inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def _resp(*blocks, stop="end_turn"):
    return NS(content=list(blocks), stop_reason=stop,
              usage=NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=100,
                       cache_creation_input_tokens=20))


class FakeClient:
    """Replays scripted responses and records every request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kwargs):
        # Snapshot the messages: the loop keeps appending to the same list.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        resp = self.responses.pop(0)

        class _Ctx:
            def __enter__(self_inner):
                return NS(get_final_message=lambda: resp)

            def __exit__(self_inner, *a):
                return False
        return _Ctx()


@pytest.fixture
def live_config():
    return make_config(mock_llm=False)


def _install(monkeypatch, responses):
    fake = FakeClient(responses)
    monkeypatch.setattr(llm, "get_client", lambda: fake)
    return fake


def test_plain_answer(monkeypatch, live_config):
    fake = _install(monkeypatch, [_resp(_text("done"))])
    assert llm.run_tool_loop(live_config, "m", "sys", [{"role": "user", "content": "q"}]) == "done"
    req = fake.requests[0]
    assert req["thinking"] == {"type": "adaptive"}
    assert req["fallbacks"] == "default"
    assert "context-management-2025-06-27" in req["betas"]


def test_tool_results_go_back_in_one_message_in_order(monkeypatch, live_config):
    fake = _install(monkeypatch, [
        _resp(_tool_use("a", "t1", x=1), _tool_use("b", "t2", x=2), stop="tool_use"),
        _resp(_text("final")),
    ])
    handlers = {"t1": lambda x: f"one{x}", "t2": lambda x: f"two{x}"}
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}],
                            tools=[{}], handlers=handlers)
    assert out == "final"
    results = fake.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert [r["content"] for r in results] == ["one1", "two2"]


def test_tool_error_is_reported_not_raised(monkeypatch, live_config):
    fake = _install(monkeypatch, [
        _resp(_tool_use("a", "boom"), stop="tool_use"),
        _resp(_text("recovered")),
    ])

    def boom():
        raise RuntimeError("403 Forbidden")
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}],
                            tools=[{}], handlers={"boom": boom})
    assert out == "recovered"
    result = fake.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "403" in result["content"]


def test_gate_pushes_back_once(monkeypatch, live_config):
    fake = _install(monkeypatch, [_resp(_text("draft")), _resp(_text("final"))])
    calls = []

    def gate(answer):
        calls.append(answer)
        return "read more"
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}], gate=gate)
    assert out == "final" and calls == ["draft"]      # second answer is not gated again
    assert fake.requests[1]["messages"][-1] == {"role": "user", "content": "read more"}


def test_round_limit_keeps_the_research(monkeypatch, live_config):
    """Out of rounds used to mean "task too big, try again". Now the model
    writes up what it has, with tools switched off."""
    loop = [_resp(_tool_use(str(i), "t"), stop="tool_use") for i in range(2)]
    fake = _install(monkeypatch, loop + [_resp(_text("partial write-up"))])
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}],
                            tools=[{}], handlers={"t": lambda: "r"}, max_rounds=2)
    assert out == "partial write-up"
    assert fake.requests[-1]["tool_choice"] == {"type": "none"}


def test_refusal_is_reported(monkeypatch, live_config):
    _install(monkeypatch, [_resp(stop="refusal")])
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}])
    assert "declined" in out


def test_usage_is_recorded(monkeypatch, live_config):
    llm.USAGE.clear()
    _install(monkeypatch, [_resp(_text("ok"))])
    llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}], agent="x")
    assert llm.USAGE["x:m"]["calls"] == 1 and llm.USAGE["x:m"]["in"] == 10
    # input_tokens excludes cache reads and writes; the summary must add them.
    assert "130 in" in llm.usage_summary()


def test_max_tokens_is_not_returned_as_empty_answer(monkeypatch, live_config):
    """A turn cut off while thinking has no text. It used to come back as ''."""
    fake = _install(monkeypatch, [
        _resp(NS(type="thinking", thinking=""), stop="max_tokens"),
        _resp(_text("short answer")),
    ])
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}])
    assert out == "short answer"
    # The truncated turn is dropped, not replayed.
    roles = [m["role"] for m in fake.requests[1]["messages"]]
    assert roles == ["user", "user"]


def test_pause_turn_continues_the_same_assistant_turn(monkeypatch, live_config):
    fake = _install(monkeypatch, [
        _resp(_text("part 1 "), stop="pause_turn"),
        _resp(_text("part 2 "), stop="pause_turn"),
        _resp(_tool_use("a", "t"), stop="tool_use"),
        _resp(_text("done")),
    ])
    out = llm.run_tool_loop(live_config, "m", "s", [{"role": "user", "content": "q"}],
                            tools=[{}], handlers={"t": lambda: "r"})
    assert out == "done"
    roles = [m["role"] for m in fake.requests[-1]["messages"]]
    assert roles == ["user", "assistant", "user"]     # one merged assistant turn
    assert len(fake.requests[-1]["messages"][1]["content"]) == 3
