"""Event system for pipeline observability.

This module provides a lightweight, thread-safe publish/subscribe
mechanism and a set of strongly-typed event dataclasses used to
observe pipeline execution. Callers may publish events to an
``EventBus`` and register handlers to respond to lifecycle, step,
task, and error events.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .context import PipelineContext
from .result import Result

T = TypeVar("T")
EventHandler = Callable[[Any], None]


@dataclass(frozen=True)
class BaseEvent:
    """Base event class that carries common event metadata.

    Subclasses add domain-specific fields such as the current
    :class:`PipelineContext` and result payloads.
    """

    timestamp: float
    run_id: str

    def __post_init__(self) -> None:
        """Perform basic validation of event fields.

        Currently this ensures the timestamp is non-negative.
        """
        if self.timestamp < 0:
            raise ValueError("Timestamp cannot be negative")


@dataclass(frozen=True)
class PipelineStartedEvent(BaseEvent):
    """Event fired when pipeline execution starts."""

    context: PipelineContext


@dataclass(frozen=True)
class PipelineCompletedEvent(BaseEvent):
    """Event fired when pipeline execution completes."""

    context: PipelineContext
    final_result: Result[Any]
    duration_ms: float


@dataclass(frozen=True)
class StepStartedEvent(BaseEvent):
    """Event fired when a step starts execution."""

    context: PipelineContext
    step_name: str
    step_type: str


@dataclass(frozen=True)
class StepCompletedEvent(BaseEvent):
    """Event fired when a step completes execution."""

    context: PipelineContext
    step_name: str
    step_type: str
    result: Result[Any]
    duration_ms: float


@dataclass(frozen=True)
class TaskStartedEvent(BaseEvent):
    """Event fired when a task starts execution."""

    context: PipelineContext
    task_name: str
    task_type: str
    step_count: int


@dataclass(frozen=True)
class TaskCompletedEvent(BaseEvent):
    """Event fired when a task completes execution."""

    context: PipelineContext
    task_name: str
    task_type: str
    final_result: Result[Any]
    duration_ms: float


@dataclass(frozen=True)
class JobStartedEvent(BaseEvent):
    """Event fired when a job starts execution."""

    context: PipelineContext
    job_name: str
    job_type: str
    task_count: int


@dataclass(frozen=True)
class JobCompletedEvent(BaseEvent):
    """Event fired when a job completes execution."""

    context: PipelineContext
    job_name: str
    job_type: str
    final_result: Result[Any]
    duration_ms: float


@dataclass(frozen=True)
class TransformationStartedEvent(BaseEvent):
    """Event fired when transformation phase starts."""

    context: PipelineContext
    transformation_type: str
    input_type: str


@dataclass(frozen=True)
class TransformationCompletedEvent(BaseEvent):
    """Event fired when transformation phase completes."""

    context: PipelineContext
    transformation_type: str
    input_type: str
    statistics: dict[str, Any]


@dataclass(frozen=True)
class ErrorEvent(BaseEvent):
    """Event fired when an error occurs."""

    context: PipelineContext
    error: Exception
    error_type: str
    component: str


class EventBus:
    """Thread-safe event publication and subscription system.

    The EventBus maintains per-event-type subscriber lists and
    guarantees that handlers are invoked outside the internal lock to
    avoid blocking publishers. Handlers are simple callables that take
    a single event instance.
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscribers: dict[type, list[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

    def clear_subscribers(self, event_type: type[T] | None = None) -> None:
        """Clear subscribers for a specific event type or all subscribers.

        Args:
            event_type: The event type whose subscribers should be cleared.
                When omitted all subscribers are removed.
        """
        with self._lock:
            if event_type:
                self._subscribers[event_type].clear()
                self._logger.debug(f"Cleared subscribers for {event_type.__name__}")
            else:
                self._subscribers.clear()
                self._logger.debug("Cleared all subscribers")

    def get_subscriber_count(self, event_type: type[T]) -> int:
        """Return the number of subscribers registered for an event type.

        Args:
            event_type: Event type to check.

        Returns:
            The number of registered subscribers.
        """
        with self._lock:
            return len(self._subscribers.get(event_type, []))

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Register a handler for events of a specific type.

        Args:
            event_type: The event dataclass/type to subscribe to.
            handler: Callable that accepts a single event instance.
        """
        with self._lock:
            self._subscribers[event_type].append(handler)
            self._logger.debug(f"Subscribed handler {handler} to {event_type.__name__}")

    def unsubscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Remove a previously registered handler for an event type.

        Args:
            event_type: Type of event to unsubscribe from.
            handler: The handler to remove.
        """
        with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                self._logger.debug(f"Unsubscribed handler {handler} from {event_type.__name__}")

    def publish(self, event: Any) -> None:
        """Publish an event to all matching subscribers.

        Handlers registered for the concrete type of ``event`` are invoked
        synchronously. Errors raised by handlers are logged but do not
        interrupt delivery to other handlers.

        Args:
            event: The event instance to publish.
        """
        event_type = type(event)
        handlers = []

        # Get handlers under lock to avoid race conditions
        with self._lock:
            handlers = self._subscribers.get(event_type, []).copy()

        # Publish to handlers outside lock for performance
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Log error but don't break pipeline
                self._logger.error(f"Event handler error for {event_type.__name__}: {e}", exc_info=True)


class EventSubscriber(ABC):
    """Base class for event subscribers.

    Subclasses should implement ``_setup_subscriptions`` to register
    handlers and ``unsubscribe_all`` to remove them.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize subscriber.

        Args:
            event_bus: Event bus to subscribe to
        """
        self.event_bus = event_bus
        self._setup_subscriptions()

    @abstractmethod
    def _setup_subscriptions(self) -> None:
        """Set up event subscriptions.

        Implementations should call ``event_bus.subscribe`` for the
        events they are interested in.
        """
        pass

    @abstractmethod
    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events.

        Subclasses should remove any handlers they previously
        subscribed with ``event_bus.unsubscribe``.
        """
        # This should be implemented by subclasses to track subscriptions
        # and remove them when called.


class LoggingSubscriber(EventSubscriber):
    """Event subscriber that logs pipeline events using the logging module.

    This subscriber registers handlers for a small set of core events
    and writes human-readable messages at appropriate logging levels.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize logging subscriber.

        Args:
            event_bus: Event bus to subscribe to
        """
        self.event_bus = event_bus
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """Set up logging subscriptions.

        Subscribes to core pipeline events and routes them to helper
        methods that produce log messages.
        """
        self.event_bus.subscribe(PipelineStartedEvent, self._on_pipeline_started)
        self.event_bus.subscribe(PipelineCompletedEvent, self._on_pipeline_completed)
        self.event_bus.subscribe(StepStartedEvent, self._on_step_started)
        self.event_bus.subscribe(StepCompletedEvent, self._on_step_completed)
        self.event_bus.subscribe(ErrorEvent, self._on_error)

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events.

        Removes the logging handlers from the event bus.
        """
        self.event_bus.unsubscribe(PipelineStartedEvent, self._on_pipeline_started)
        self.event_bus.unsubscribe(PipelineCompletedEvent, self._on_pipeline_completed)
        self.event_bus.unsubscribe(StepStartedEvent, self._on_step_started)
        self.event_bus.unsubscribe(StepCompletedEvent, self._on_step_completed)
        self.event_bus.unsubscribe(ErrorEvent, self._on_error)

    def _on_pipeline_started(self, event: PipelineStartedEvent) -> None:
        """Handle pipeline started event.

        Logs an informational message including source and target
        files and the current run id.
        """
        self.event_bus._logger.info(
            f"Pipeline started: {event.context.source_file} -> {event.context.target_file} (run_id: {event.run_id})"
        )

    def _on_pipeline_completed(self, event: PipelineCompletedEvent) -> None:
        """Handle pipeline completed event.

        Logs completion status and the elapsed duration in milliseconds.
        """
        status = "SUCCESS" if event.final_result.is_success() else "FAILED"
        self.event_bus._logger.info(f"Pipeline completed in {event.duration_ms:.2f}ms: {status}")

    def _on_step_started(self, event: StepStartedEvent) -> None:
        """Handle step started event.

        Emit a debug-level message that includes the step name and type.
        """
        self.event_bus._logger.debug(f"Step started: {event.step_name} ({event.step_type})")

    def _on_step_completed(self, event: StepCompletedEvent) -> None:
        """Handle step completed event.

        Logs the step duration and status at debug level.
        """
        status = event.result.status.value.upper()
        self.event_bus._logger.debug(f"Step completed in {event.duration_ms:.2f}ms: {event.step_name} ({status})")

    def _on_error(self, event: ErrorEvent) -> None:
        """Handle error event.

        Logs the exception with traceback information.
        """
        self.event_bus._logger.error(f"Error in {event.component}: {event.error}", exc_info=True)


class EventTimer:
    """Utility class for timing operations and publishing events."""

    def __init__(self, event_bus: EventBus, run_id: str):
        """Initialize timer.

        Args:
            event_bus: Event bus to publish events to
            run_id: Current run ID
        """
        self.event_bus = event_bus
        self.run_id = run_id
        self._start_times: dict[str, float] = {}
        self._contexts: dict[str, PipelineContext] = {}

    def start_operation(self, operation_name: str, context: PipelineContext) -> None:
        """Start timing an operation.

        Args:
            operation_name: Name of the operation
            context: Pipeline context
        """
        self._start_times[operation_name] = time.time()
        self._contexts[operation_name] = context

    def end_operation(self, operation_name: str, result: Result[Any]) -> float:
        """End timing an operation and publish completion event.

        Args:
            operation_name: Name of the operation
            result: Result of the operation

        Returns:
            Duration in milliseconds
        """
        if operation_name not in self._start_times:
            raise ValueError(f"Operation {operation_name} was not started")

        start_time = self._start_times[operation_name]
        context = self._contexts[operation_name]
        duration_ms = (time.time() - start_time) * 1000

        # Publish appropriate completion event based on operation type
        if "step" in operation_name.lower():
            step_event = StepCompletedEvent(
                timestamp=time.time(),
                run_id=self.run_id,
                context=context,
                step_name=operation_name,
                step_type=operation_name.split("_")[0],
                result=result,
                duration_ms=duration_ms,
            )
            self.event_bus.publish(step_event)
        elif "task" in operation_name.lower():
            task_event = TaskCompletedEvent(
                timestamp=time.time(),
                run_id=self.run_id,
                context=context,
                task_name=operation_name,
                task_type=operation_name.split("_")[0],
                final_result=result,
                duration_ms=duration_ms,
            )
            self.event_bus.publish(task_event)
        elif "job" in operation_name.lower():
            job_event = JobCompletedEvent(
                timestamp=time.time(),
                run_id=self.run_id,
                context=context,
                job_name=operation_name,
                job_type=operation_name.split("_")[0],
                final_result=result,
                duration_ms=duration_ms,
            )
            self.event_bus.publish(job_event)
        else:
            # Fallback for unknown operation types
            fallback_event = StepCompletedEvent(
                timestamp=time.time(),
                run_id=self.run_id,
                context=context,
                step_name=operation_name,
                step_type="unknown",
                result=result,
                duration_ms=duration_ms,
            )
            self.event_bus.publish(fallback_event)

        # Clean up
        del self._start_times[operation_name]
        del self._contexts[operation_name]

        return duration_ms
