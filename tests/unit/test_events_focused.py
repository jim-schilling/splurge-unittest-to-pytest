import time

from splurge_unittest_to_pytest.events import EventBus, EventTimer, StepCompletedEvent


def test_eventbus_subscribe_publish_and_timer_publish():
    bus = EventBus()
    received = []

    def handler(evt):
        received.append(type(evt))

    bus.subscribe(StepCompletedEvent, handler)
    # publish a StepCompletedEvent
    evt = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {"source_file": "s", "target_file": "t", "run_id": "r"})(),
        step_name="s",
        step_type="st",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=1.0,
    )
    bus.publish(evt)
    assert StepCompletedEvent in received

    # Test EventTimer start/end flow publishes events
    ctx = type("Ctx", (), {"source_file": "s", "target_file": "t", "run_id": "rid"})()
    timer = EventTimer(bus, run_id="rid")
    timer.start_operation("step_write", ctx)
    res = type("R2", (), {"status": type("S2", (), {"value": "ok"})()})()
    dur = timer.end_operation("step_write", res)
    assert isinstance(dur, float)


def test_eventbus_publish_handler_raises_but_others_receive():
    bus = EventBus()
    calls = []

    def a(evt):
        calls.append("a")

    def b(evt):
        calls.append("b")
        raise RuntimeError("boom")

    def c(evt):
        calls.append("c")

    bus.subscribe(StepCompletedEvent, a)
    bus.subscribe(StepCompletedEvent, b)
    bus.subscribe(StepCompletedEvent, c)

    evt = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=0.1,
    )
    # Should not raise despite b raising
    bus.publish(evt)
    assert calls[0] == "a"
    # b should have been called and appended before raising
    assert "b" in calls
    assert "c" in calls
