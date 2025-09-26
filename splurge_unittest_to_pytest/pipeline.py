"""Pipeline architecture for functional composition.

This module provides the core pipeline architecture with Step, Task, and Job
abstractions that enable functional composition of operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from .context import PipelineContext
from .events import EventBus, StepCompletedEvent, StepStartedEvent
from .result import Result, ResultStatus

T = TypeVar("T")
R = TypeVar("R")
U = TypeVar("U")


class Step(ABC, Generic[T, R]):
    """Atomic operation with single responsibility.

    Steps are the smallest unit of work in the pipeline. Each step
    takes input of type T and produces output of type R.
    """

    def __init__(self, name: str, event_bus: EventBus) -> None:
        """Initialize step.

        Args:
            name: Unique name for this step
            event_bus: Event bus for publishing events
        """
        self.name = name
        self.event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def execute(self, context: PipelineContext, input_data: T) -> Result[R]:
        """Pure transformation function.

        Args:
            context: Pipeline execution context
            input_data: Input data for transformation

        Returns:
            Result containing transformed data or error
        """
        pass

    def run(self, context: PipelineContext, input_data: T) -> Result[R]:
        """Execute step with event publishing and error handling.

        Args:
            context: Pipeline execution context
            input_data: Input data for transformation

        Returns:
            Result containing transformed data or error
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
        """Get current timestamp.

        Returns:
            Current timestamp in seconds
        """
        import time

        return time.time()


class Task(Generic[T, R]):
    """Collection of related steps.

    Tasks compose multiple steps together, executing them in sequence
    and short-circuiting on errors.
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
        """Execute steps in sequence with short-circuit on error.

        Args:
            context: Pipeline execution context
            input_data: Input data for the first step

        Returns:
            Result containing final transformed data or first error
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
            step: Step to add
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
    """High-level processing unit.

    Jobs compose multiple tasks together, providing high-level
    orchestration of complex operations.
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

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[R]:
        """Execute all tasks with context threading.

        Args:
            context: Pipeline execution context
            initial_input: Initial input data for the first task

        Returns:
            Result containing final transformed data or first error
        """
        self._logger.info(f"Starting job: {self.name} with {len(self.tasks)} tasks")

        current_context = context
        task_results = []
        current_input = initial_input

        for i, task in enumerate(self.tasks):
            self._logger.debug(f"Executing task {i + 1}/{len(self.tasks)}: {task.name}")

            result = task.execute(current_context, current_input)

            if result.is_error():
                self._logger.error(f"Task {task.name} failed, aborting job {self.name}")
                error = result.error or RuntimeError(f"Job {self.name} failed at task {task.name}")
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

        # Return successful result with combined warnings
        final_result = task_results[-1]
        if all_warnings:
            return Result.warning(final_result.data, all_warnings, final_result.metadata)  # type: ignore

        return Result.success(final_result.data, final_result.metadata)  # type: ignore

    def add_task(self, task: Task) -> None:
        """Add a task to the job.

        Args:
            task: Task to add
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

    The pipeline coordinates the execution of jobs and manages
    the overall flow of data transformation.
    """

    def __init__(self, name: str, jobs: list[Job], event_bus: EventBus) -> None:
        """Initialize pipeline.

        Args:
            name: Unique name for this pipeline
            jobs: List of jobs to execute in order
            event_bus: Event bus for publishing events
        """
        self.name = name
        self.jobs = jobs
        self.event_bus = event_bus
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[R]:
        """Execute the entire pipeline.

        Args:
            context: Pipeline execution context
            initial_input: Initial input data for the pipeline

        Returns:
            Result containing final transformed data or first error
        """
        self._logger.info(f"Starting pipeline: {self.name} with {len(self.jobs)} jobs")

        current_context = context
        job_results = []
        current_input = initial_input

        for i, job in enumerate(self.jobs):
            self._logger.debug(f"Executing job {i + 1}/{len(self.jobs)}: {job.name}")

            result = job.execute(current_context, current_input)

            if result.is_error():
                self._logger.error(f"Job {job.name} failed, aborting pipeline {self.name}")
                error = result.error or RuntimeError(f"Pipeline {self.name} failed at job {job.name}")
                return Result.failure(
                    error,
                    {"pipeline": self.name, "failed_job": job.name, "job_index": i, "context": context.run_id},
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

        # Return successful result with combined warnings
        final_result = job_results[-1]
        if all_warnings:
            return Result.warning(final_result.data, all_warnings, final_result.metadata)  # type: ignore

        return Result.success(final_result.data, final_result.metadata)  # type: ignore

    def add_job(self, job: Job) -> None:
        """Add a job to the pipeline.

        Args:
            job: Job to add
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
