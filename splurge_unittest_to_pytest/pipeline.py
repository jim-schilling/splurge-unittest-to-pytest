"""Pipeline architecture for functional composition.

This module provides the core pipeline architecture with ``Step``,
``Task``, and ``Job`` abstractions that enable functional composition of
operations.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker
from .context import PipelineContext
from .events import (
    EventBus,
    JobCompletedEvent,
    JobStartedEvent,
    PipelineCompletedEvent,
    PipelineStartedEvent,
    StepCompletedEvent,
    StepStartedEvent,
)
from .result import Result, ResultStatus

T = TypeVar("T")
R = TypeVar("R")
U = TypeVar("U")


class Step(ABC, Generic[T, R]):
    """Atomic operation with a single responsibility.

    A ``Step`` transforms input of type ``T`` into output of type
    ``R``. Concrete steps implement ``execute`` and are run with the
    ``run`` helper that publishes start/completion events and handles
    exceptions.
    """

    def __init__(self, name: str, event_bus: EventBus) -> None:
        """Initialize step.

        Args:
            name: Unique name for this step.
            event_bus: Event bus for publishing events.
        """
        self.name = name
        self.event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def execute(self, context: PipelineContext, input_data: T) -> Result[R]:
        """Pure transformation function to implement in subclasses.

        Args:
            context: Pipeline execution context.
            input_data: Input data for transformation.

        Returns:
            ``Result`` containing transformed data or an error.
        """
        pass

    def run(self, context: PipelineContext, input_data: T) -> Result[R]:
        """Execute the step with event publishing and error handling.

        This helper publishes ``StepStartedEvent`` and ``StepCompletedEvent``
        around the call to ``execute`` and converts exceptions into an
        error ``Result``.

        Args:
            context: Pipeline execution context.
            input_data: Input data for transformation.

        Returns:
            ``Result`` containing transformed data or an error.
        """
        # Publish start event
        start_event = StepStartedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
            step_name=self.name,
            step_type=self.__class__.__name__,
        )
        self.event_bus.publish(start_event)

        start_time = self._get_timestamp()

        try:
            self._logger.debug(f"Starting step: {self.name}")
            result = self.execute(context, input_data)
            self._logger.debug(f"Completed step: {self.name} ({result.status.value})")
        except Exception as e:
            self._logger.error(f"Exception in step {self.name}: {e}", exc_info=True)
            result = Result.failure(e, {"step": self.name, "context": context.run_id})

        duration_ms = (self._get_timestamp() - start_time) * 1000

        # Publish completion event
        completion_event = StepCompletedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
            step_name=self.name,
            step_type=self.__class__.__name__,
            result=result,
            duration_ms=duration_ms,
        )
        self.event_bus.publish(completion_event)

        return result

    def _get_timestamp(self) -> float:
        """Get current timestamp in seconds.

        Returns:
            Current timestamp in seconds (float).
        """
        import time

        return time.time()


class Task(Generic[T, R]):
    """Collection of related steps executed sequentially.

    A ``Task`` composes multiple ``Step`` instances and threads data
    through them, short-circuiting when a step produces an error.
    """

    def __init__(self, name: str, steps: list[Step], event_bus: EventBus) -> None:
        """Initialize task.

        Args:
            name: Unique name for this task
            steps: List of steps to execute in order
            event_bus: Event bus for publishing events
        """
        self.name = name
        self.steps = steps
        self.event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def execute(self, context: PipelineContext, input_data: T) -> Result[R]:
        """Execute the configured steps in sequence.

        Args:
            context: Pipeline execution context.
            input_data: Input data for the first step.

        Returns:
            ``Result`` containing the final transformed data on success or
            the first error encountered.
        """
        self._logger.debug(f"Starting task: {self.name} with {len(self.steps)} steps")

        current_data = input_data
        step_results = []

        for i, step in enumerate(self.steps):
            self._logger.debug(f"Executing step {i + 1}/{len(self.steps)}: {step.name}")

            result = step.run(context, current_data)

            if result.is_error():
                self._logger.error(f"Step {step.name} failed, aborting task {self.name}")
                error = result.error or RuntimeError(f"Task {self.name} failed at step {step.name}")
                return Result.failure(
                    error,
                    {"task": self.name, "failed_step": step.name, "step_index": i, "context": context.run_id},
                )

            step_results.append(result)

            # Thread data through pipeline
            if result.data is not None:
                current_data = result.data
            elif result.status == ResultStatus.WARNING and current_data is not None:
                # Keep the current data even if the warning result has None data
                pass

        # Combine warnings from all steps
        all_warnings: list[str] = []
        for result in step_results:
            if result.warnings:
                all_warnings.extend(result.warnings)

        # Return successful result with combined warnings
        final_result = step_results[-1]
        if all_warnings:
            return Result.warning(final_result.data, all_warnings, final_result.metadata)  # type: ignore

        return Result.success(final_result.data, final_result.metadata)  # type: ignore

    def add_step(self, step: Step) -> None:
        """Add a step to the task.

        Args:
            step: Step instance to append to this task.
        """
        self.steps.append(step)
        self._logger.debug(f"Added step {step.name} to task {self.name}")

    def get_step_count(self) -> int:
        """Get number of steps in this task.

        Returns:
            Number of steps
        """
        return len(self.steps)


class Job(Generic[T, R]):
    """High-level processing unit composed of tasks.

    Jobs orchestrate multiple ``Task`` instances and provide higher-level
    error aggregation and context threading.
    """

    def __init__(self, name: str, tasks: list[Task], event_bus: EventBus) -> None:
        """Initialize job.

        Args:
            name: Unique name for this job
            tasks: List of tasks to execute in order
            event_bus: Event bus for publishing events
        """
        self.name = name
        self.tasks = tasks
        self.event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def _get_timestamp(self) -> float:
        """Get current timestamp for event publishing.

        Returns:
            Current timestamp as float
        """
        import time

        return time.time()

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[R]:
        """Execute all tasks and thread context/data through them.

        Args:
            context: Pipeline execution context.
            initial_input: Optional initial input for the first task.

        Returns:
            ``Result`` containing final transformed data on success or the
            first encountered error.
        """
        # Publish job started event
        start_event = JobStartedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
            job_name=self.name,
            job_type=self.__class__.__name__,
            task_count=len(self.tasks),
        )
        self.event_bus.publish(start_event)

        self._logger.info(f"Starting job: {self.name} with {len(self.tasks)} tasks")
        start_time = self._get_timestamp()

        current_context = context
        task_results = []
        current_input = initial_input

        for i, task in enumerate(self.tasks):
            self._logger.debug(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            result = task.execute(current_context, current_input)

            if result.is_error():
                self._logger.error(f"Task {task.name} failed, aborting job {self.name}")
                error = result.error or RuntimeError(f"Job {self.name} failed at task {task.name}")

                # Publish job completed event with error
                duration_ms = (self._get_timestamp() - start_time) * 1000
                completion_event = JobCompletedEvent(
                    timestamp=self._get_timestamp(),
                    run_id=context.run_id,
                    context=context,
                    job_name=self.name,
                    job_type=self.__class__.__name__,
                    final_result=result,
                    duration_ms=duration_ms,
                )
                self.event_bus.publish(completion_event)

                return Result.failure(
                    error,
                    {"job": self.name, "failed_task": task.name, "task_index": i, "context": context.run_id},
                )

            task_results.append(result)

            # Thread context and data through pipeline
            if isinstance(result.data, PipelineContext):
                current_context = result.data
            elif result.data is not None:
                # Use result data as input for next task (works for success and warning results)
                current_input = result.data

        # Combine warnings from all tasks
        all_warnings: list[str] = []
        for result in task_results:
            if result.warnings:
                all_warnings.extend(result.warnings)

        # Calculate duration and publish completion event
        duration_ms = (self._get_timestamp() - start_time) * 1000
        final_result = task_results[-1]

        # Publish job completed event
        completion_event = JobCompletedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
            job_name=self.name,
            job_type=self.__class__.__name__,
            final_result=final_result,
            duration_ms=duration_ms,
        )
        self.event_bus.publish(completion_event)

        # Return successful result with combined warnings
        if all_warnings:
            return Result.warning(final_result.data, all_warnings, final_result.metadata)  # type: ignore

        return Result.success(final_result.data, final_result.metadata)  # type: ignore

    def add_task(self, task: Task) -> None:
        """Add a task to the job.

        Args:
            task: Task instance to append to this job.
        """
        self.tasks.append(task)
        self._logger.debug(f"Added task {task.name} to job {self.name}")

    def get_task_count(self) -> int:
        """Get number of tasks in this job.

        Returns:
            Number of tasks
        """
        return len(self.tasks)


class Pipeline(Generic[T, R]):
    """Main pipeline orchestrator.

    The pipeline coordinates execution of ``Job`` instances and manages
    overall data and context flow.
    """

    circuit_breaker: CircuitBreaker | None

    def __init__(
        self,
        name: str,
        jobs: list[Job],
        event_bus: EventBus,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize pipeline.

        Args:
            name: Unique name for this pipeline
            jobs: List of jobs to execute in order
            event_bus: Event bus for publishing events
            circuit_breaker_config: Optional circuit breaker configuration
        """
        self.name = name
        self.jobs = jobs
        self.event_bus = event_bus
        self.circuit_breaker_config = circuit_breaker_config
        self._logger = logging.getLogger(f"{__name__}.{name}")

        # Create circuit breaker for this pipeline
        if circuit_breaker_config:
            self.circuit_breaker = get_circuit_breaker(f"pipeline_{name}", circuit_breaker_config)
        else:
            self.circuit_breaker = None

    def _get_timestamp(self) -> float:
        """Get current timestamp for event publishing.

        Returns:
            Current timestamp as float
        """
        import time

        return time.time()

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[R]:
        """Execute all jobs in the pipeline in order.

        Args:
            context: Pipeline execution context.
            initial_input: Optional initial input for the pipeline.

        Returns:
            ``Result`` containing final transformed data on success or the
            first error encountered.
        """
        # Publish pipeline started event
        start_event = PipelineStartedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
        )
        self.event_bus.publish(start_event)

        start_time = self._get_timestamp()
        self._logger.info(f"Starting pipeline: {self.name} with {len(self.jobs)} jobs")

        current_context = context
        job_results = []
        current_input = initial_input

        for i, job in enumerate(self.jobs):
            self._logger.debug(f"Executing job {i + 1}/{len(self.jobs)}: {job.name}")

            try:
                # Use circuit breaker recovery if configured
                if self.circuit_breaker:
                    result = self.circuit_breaker.attempt_recovery(job.execute, current_context, current_input)
                else:
                    result = job.execute(current_context, current_input)

                if result.is_error():
                    self._logger.error(f"Job {job.name} failed, aborting pipeline {self.name}")
                    error = result.error or RuntimeError(f"Pipeline {self.name} failed at job {job.name}")

                    # Publish pipeline completed event with error
                    duration_ms = (self._get_timestamp() - start_time) * 1000
                    completion_event = PipelineCompletedEvent(
                        timestamp=self._get_timestamp(),
                        run_id=context.run_id,
                        context=context,
                        final_result=result,
                        duration_ms=duration_ms,
                    )
                    self.event_bus.publish(completion_event)

                    return Result.failure(
                        error,
                        {"pipeline": self.name, "failed_job": job.name, "job_index": i, "context": context.run_id},
                    )
            except Exception as e:
                # Circuit breaker open or other execution error
                self._logger.error(f"Job {job.name} execution failed with circuit breaker protection: {e}")

                # Publish pipeline completed event with exception
                duration_ms = (self._get_timestamp() - start_time) * 1000
                error_result: Result[R] = Result.failure(e)
                completion_event = PipelineCompletedEvent(
                    timestamp=self._get_timestamp(),
                    run_id=context.run_id,
                    context=context,
                    final_result=error_result,
                    duration_ms=duration_ms,
                )
                self.event_bus.publish(completion_event)

                return Result.failure(
                    e,
                    {
                        "pipeline": self.name,
                        "failed_job": job.name,
                        "job_index": i,
                        "context": context.run_id,
                        "circuit_breaker_protected": self.circuit_breaker is not None,
                    },
                )

            job_results.append(result)

            # Thread context and data through pipeline
            if isinstance(result.data, PipelineContext):
                current_context = result.data
            elif result.is_success():
                # Use result data as input for next job
                current_input = result.data

        # Combine warnings from all jobs
        all_warnings: list[str] = []
        for result in job_results:
            if result.warnings:
                all_warnings.extend(result.warnings)

        # Calculate duration and publish completion event
        duration_ms = (self._get_timestamp() - start_time) * 1000
        final_result = job_results[-1]

        # Publish pipeline completed event
        completion_event = PipelineCompletedEvent(
            timestamp=self._get_timestamp(),
            run_id=context.run_id,
            context=context,
            final_result=final_result,
            duration_ms=duration_ms,
        )
        self.event_bus.publish(completion_event)

        # Return successful result with combined warnings
        if all_warnings:
            return Result.warning(final_result.data, all_warnings, final_result.metadata)

        return Result.success(final_result.data, final_result.metadata)

    def add_job(self, job: Job) -> None:
        """Add a job to the pipeline.

        Args:
            job: Job instance to append to this pipeline.
        """
        self.jobs.append(job)
        self._logger.debug(f"Added job {job.name} to pipeline {self.name}")

    def get_job_count(self) -> int:
        """Get number of jobs in this pipeline.

        Returns:
            Number of jobs
        """
        return len(self.jobs)


class PipelineFactory:
    """Factory for creating pipeline instances."""

    def __init__(self, event_bus: EventBus):
        """Initialize factory.

        Args:
            event_bus: Event bus for pipeline components
        """
        self.event_bus = event_bus

    def create_step(self, name: str, step_class: type[Step[Any, Any]], **kwargs: Any) -> Step[Any, Any]:
        """Create a step instance.

        Args:
            name: Name for the step
            step_class: Class to instantiate
            **kwargs: Additional arguments for step constructor

        Returns:
            Configured step instance
        """
        return step_class(name, self.event_bus, **kwargs)

    def create_task(self, name: str, steps: list[Step]) -> Task:
        """Create a task instance.

        Args:
            name: Name for the task
            steps: List of steps to include

        Returns:
            Configured task instance
        """
        return Task(name, steps, self.event_bus)

    def create_job(self, name: str, tasks: list[Task]) -> Job:
        """Create a job instance.

        Args:
            name: Name for the job
            tasks: List of tasks to include

        Returns:
            Configured job instance
        """
        return Job(name, tasks, self.event_bus)

    def create_pipeline(self, name: str, jobs: list[Job]) -> Pipeline:
        """Create a pipeline instance.

        Args:
            name: Name for the pipeline
            jobs: List of jobs to include

        Returns:
            Configured pipeline instance
        """
        return Pipeline(name, jobs, self.event_bus)

        # Import concrete implementations from dedicated modules
