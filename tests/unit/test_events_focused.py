import time

import pytest

from splurge_unittest_to_pytest.events import (
    ErrorEvent,
    EventBus,
    EventTimer,
    LoggingSubscriber,
    StepCompletedEvent,
    StepStartedEvent,
)


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


def test_eventbus_clear_subscribers_specific_type():
    """Test clearing subscribers for a specific event type."""
    bus = EventBus()
    calls = []

    def handler(evt):
        calls.append("called")

    # Subscribe to two event types
    bus.subscribe(StepCompletedEvent, handler)
    bus.subscribe(StepStartedEvent, handler)

    # Clear only StepCompletedEvent subscribers
    bus.clear_subscribers(StepCompletedEvent)

    # StepCompletedEvent should not trigger handler
    evt1 = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=0.1,
    )
    bus.publish(evt1)
    assert len(calls) == 0

    # StepStartedEvent should still trigger handler
    evt2 = StepStartedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
    )
    bus.publish(evt2)
    assert len(calls) == 1


def test_eventbus_clear_subscribers_all():
    """Test clearing all subscribers."""
    bus = EventBus()
    calls = []

    def handler(evt):
        calls.append("called")

    # Subscribe to events
    bus.subscribe(StepCompletedEvent, handler)
    bus.subscribe(StepStartedEvent, handler)

    # Clear all subscribers
    bus.clear_subscribers()

    # Neither event should trigger handler
    evt1 = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=0.1,
    )
    bus.publish(evt1)

    evt2 = StepStartedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
    )
    bus.publish(evt2)

    assert len(calls) == 0


def test_eventbus_get_subscriber_count():
    """Test getting subscriber count for event types."""
    bus = EventBus()

    def handler1(evt):
        pass

    def handler2(evt):
        pass

    # Initially no subscribers
    assert bus.get_subscriber_count(StepCompletedEvent) == 0

    # Add subscribers
    bus.subscribe(StepCompletedEvent, handler1)
    assert bus.get_subscriber_count(StepCompletedEvent) == 1

    bus.subscribe(StepCompletedEvent, handler2)
    assert bus.get_subscriber_count(StepCompletedEvent) == 2

    # Different event type has no subscribers
    assert bus.get_subscriber_count(StepStartedEvent) == 0


def test_eventbus_unsubscribe():
    """Test unsubscribing handlers."""
    bus = EventBus()
    calls = []

    def handler1(evt):
        calls.append("handler1")

    def handler2(evt):
        calls.append("handler2")

    # Subscribe both handlers
    bus.subscribe(StepCompletedEvent, handler1)
    bus.subscribe(StepCompletedEvent, handler2)

    # Publish event - both should be called
    evt = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=0.1,
    )
    bus.publish(evt)
    assert len(calls) == 2

    # Unsubscribe handler1
    bus.unsubscribe(StepCompletedEvent, handler1)

    # Reset calls and publish again - only handler2 should be called
    calls.clear()
    bus.publish(evt)
    assert len(calls) == 1
    assert calls[0] == "handler2"


def test_logging_subscriber_error_handling(mocker):
    """Test LoggingSubscriber error event handling."""
    bus = EventBus()
    LoggingSubscriber(bus)

    # Mock logger to capture calls
    mock_logger = mocker.patch.object(bus, "_logger")

    # Create and publish error event
    error_event = ErrorEvent(
        timestamp=time.time(),
        run_id="test_run",
        component="test_component",
        error=ValueError("test error"),
        error_type="ValueError",
        context=type("C", (), {})(),
    )

    bus.publish(error_event)

    # Verify logger.error was called with exc_info=True
    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert call_args[0][0] == "Error in test_component: test error"
    assert call_args[1]["exc_info"] is True
