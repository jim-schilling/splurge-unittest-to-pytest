"""Decision analysis job for multi-pass transformation analysis.

This job performs static analysis of unittest source files to build
a decision model that informs transformation strategies. It runs
the 4 analysis passes (module, class, function scanning + proposal
reconciliation) without performing any actual transformations.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
from typing import Any, Literal

import libcst as cst

from ..context import PipelineContext
from ..decision_model import ClassProposal, DecisionModel, FunctionProposal, ModuleProposal
from ..events import EventBus
from ..exceptions import AnalysisStepError, ContextError
from ..pipeline import Job, Step, Task
from ..result import Result


class DecisionAnalysisJob(Job[str, DecisionModel]):
    """Analyze unittest source files and build decision models.

    This job coordinates the 4 analysis passes:
    1. Module scanner - collect module-level facts
    2. Class scanner - collect class-level facts
    3. Function scanner - detect transformation opportunities
    4. Bubbler - reconcile and aggregate proposals

    The job outputs a DecisionModel without performing any transformations.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize the decision analysis job.

        Args:
            event_bus: Event bus used for publishing pipeline events.
        """
        super().__init__("decision_analysis", [self._create_analysis_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_analysis_task(self, event_bus: EventBus) -> Task[str, DecisionModel]:
        """Create and return the analysis task for this job."""
        from ..pipeline import Task

        return Task(
            name="analyze_source",
            steps=[
                ParseSourceForAnalysisStep("parse_for_analysis", event_bus),
                ModuleScannerStep("module_scanner", event_bus),
                ClassScannerStep("class_scanner", event_bus),
                FunctionScannerStep("function_scanner", event_bus),
                ProposalReconcilerStep("proposal_reconciler", event_bus),
            ],
            event_bus=event_bus,
        )


class ParseSourceForAnalysisStep(Step[str, cst.Module]):
    """Parse source code into CST for analysis."""

    def __init__(self, name: str, event_bus: EventBus) -> None:
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, input_data: str) -> Result[cst.Module]:
        """Parse source code into CST module."""
        try:
            self._logger.debug("Parsing source code for analysis")

            # Parse the source code into a CST module
            module = cst.parse_module(input_data)

            # Store the CST module in context for downstream steps
            context.metadata["cst_module"] = module

            return Result.success(module)

        except Exception as e:
            self._logger.error(f"Failed to parse source code: {e}")
            error = AnalysisStepError(
                f"Failed to parse source code: {e}", "parse_source", module_name=context.source_file
            )
            return Result.failure(error, {"step": self.name, "context": context.run_id})


class ModuleScannerStep(Step[cst.Module, cst.Module]):
    """Scan module-level constructs and collect metadata."""

    def __init__(self, name: str, event_bus: EventBus) -> None:
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, input_data: cst.Module) -> Result[cst.Module]:
        """Scan module for top-level assignments, imports, and fixtures."""
        try:
            self._logger.debug("Scanning module-level constructs")

            module_name = context.source_file or "unknown"

            # Collect module-level information
            module_imports = self._collect_imports(input_data)
            top_level_assignments = self._collect_top_level_assignments(input_data)
            module_fixtures = self._collect_module_fixtures(input_data)

            module_proposal = ModuleProposal(
                module_name=module_name,
                class_proposals={},
                module_fixtures=module_fixtures,
                module_imports=module_imports,
                top_level_assignments=top_level_assignments,
            )

            # Store module proposal in context for downstream steps
            context.metadata["module_proposal"] = module_proposal

            return Result.success(input_data)

        except Exception as e:
            self._logger.error(f"Failed to scan module: {e}")
            error = AnalysisStepError(f"Failed to scan module: {e}", "module_scanner", module_name=context.source_file)
            return Result.failure(error, {"step": self.name, "context": context.run_id})

    def _collect_imports(self, module: cst.Module) -> list[str]:
        """Collect import statements from the module."""
        def _extract_name_value(obj: Any) -> str | None:
            """Return the .value for a cst.Name or None."""
            if isinstance(obj, cst.Name) and getattr(obj, "value", None):
                return obj.value
            return None

        imports = []
        try:
            for node in module.body:
                # Handle SimpleStatementLine wrapper
                stmt: Any
                if isinstance(node, cst.SimpleStatementLine):
                    stmt = node.body[0] if node.body else None
                else:
                    stmt = node

                if isinstance(stmt, cst.Import):
                    # stmt.names may be a sequence of ImportAlias
                    for alias in getattr(stmt, "names", ()):
                        name_obj = getattr(alias, "name", None)
                        asname_obj = getattr(alias, "asname", None)
                        name_val = _extract_name_value(name_obj)
                        if name_val:
                            imports.append(f"import {name_val}")
                        if isinstance(asname_obj, cst.AsName):
                            asname_name = getattr(asname_obj, "name", None)
                            asname_val = _extract_name_value(asname_name)
                            if asname_val and name_val:
                                imports.append(f"import {name_val} as {asname_val}")
                elif isinstance(stmt, cst.ImportFrom):
                    module_name = getattr(stmt.module, "value", "") if getattr(stmt, "module", None) else ""
                    for alias in getattr(stmt, "names", ()):  # handle ImportStar vs aliases
                        name_obj = getattr(alias, "name", None)
                        asname_obj = getattr(alias, "asname", None)
                        name_val = _extract_name_value(name_obj)
                        if name_val:
                            import_name = f"from {module_name} import {name_val}"
                            if isinstance(asname_obj, cst.AsName):
                                asname_name = getattr(asname_obj, "name", None)
                                asname_val = _extract_name_value(asname_name)
                                if asname_val:
                                    import_name += f" as {asname_val}"
                            imports.append(import_name)
        except Exception as e:
            self._logger.warning(f"Error collecting imports: {e}")
        return imports

    def _collect_top_level_assignments(self, module: cst.Module) -> dict[str, str]:
        """Collect top-level variable assignments."""
        assignments = {}
        try:
            for node in module.body:
                # Handle SimpleStatementLine wrapper
                stmt: Any
                if isinstance(node, cst.SimpleStatementLine):
                    stmt = node.body[0] if node.body else None
                else:
                    stmt = node

                if isinstance(stmt, cst.Assign):
                    for target in stmt.targets:
                        tgt = getattr(target, "target", None)
                        if isinstance(tgt, cst.Name):
                            var_name = tgt.value
                            # Try to get a simple representation of the value
                            val = getattr(stmt, "value", None)
                            if isinstance(val, cst.List | cst.Tuple):
                                assignments[var_name] = f"{type(val).__name__} (literal)"
                            elif isinstance(val, cst.Name) and getattr(val, "value", None):
                                assignments[var_name] = f"reference to {val.value}"
                            elif isinstance(val, cst.Call):
                                assignments[var_name] = "function call"
                            else:
                                assignments[var_name] = f"{type(val).__name__}"
        except Exception as e:
            self._logger.warning(f"Error collecting assignments: {e}")
        return assignments

    def _collect_module_fixtures(self, module: cst.Module) -> list[str]:
        """Collect module-level fixtures (pytest fixtures or similar)."""
        fixtures = []
        try:
            # Look for @pytest.fixture decorators or similar patterns
            for node in module.body:
                # Handle SimpleStatementLine wrapper for function definitions
                if isinstance(node, cst.SimpleStatementLine):
                    continue  # Skip for now, focus on direct FunctionDef nodes

                if isinstance(node, cst.FunctionDef):
                    # Check for pytest fixture decorators
                    for decorator in node.decorators:
                        dec = getattr(decorator, "decorator", None)
                        if isinstance(dec, cst.Call):
                            func = getattr(dec, "func", None)
                            if isinstance(func, cst.Attribute):
                                func_val = getattr(func, "value", None)
                                func_attr = getattr(func, "attr", None)
                                if isinstance(func_val, cst.Name) and getattr(func_val, "value", None) == "pytest" and isinstance(func_attr, cst.Name) and getattr(func_attr, "value", None) == "fixture":
                                    fixtures.append(node.name.value)
                        elif isinstance(dec, cst.Name) and getattr(dec, "value", None) == "fixture":
                            # Handle @fixture decorator (pytest style)
                            fixtures.append(node.name.value)
        except Exception as e:
            self._logger.warning(f"Error collecting fixtures: {e}")
        return fixtures


class ClassScannerStep(Step[cst.Module, cst.Module]):
    """Scan class-level constructs and collect metadata."""

    def __init__(self, name: str, event_bus: EventBus) -> None:
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, input_data: cst.Module) -> Result[cst.Module]:
        """Scan classes for fixtures and setup methods."""
        try:
            self._logger.debug("Scanning class-level constructs")

            # If the metadata does not contain the key at all, treat as an error.
            if "module_proposal" not in context.metadata:
                ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            module_proposal = context.metadata.get("module_proposal")
            # If the key exists but the value is None, and we have a CST module,
            # synthesize a ModuleProposal for in-memory analysis (tests do this).
            if module_proposal is None:
                cst_mod = context.metadata.get("cst_module")
                if cst_mod is not None:
                    module_name = context.source_file or "unknown"
                    module_proposal = ModuleProposal(
                        module_name=module_name,
                        class_proposals={},
                        module_fixtures=[],
                        module_imports=[],
                        top_level_assignments={},
                    )
                    context.metadata["module_proposal"] = module_proposal
                else:
                    ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                    return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            # Scan all classes in the module
            for node in input_data.body:
                if isinstance(node, cst.ClassDef):
                    self._scan_class(node, module_proposal)

            return Result.success(input_data)

        except Exception as e:
            self._logger.error(f"Failed to scan classes: {e}")
            analysis_error = AnalysisStepError(f"Failed to scan classes: {e}", "class_scanner", module_name=context.source_file)
            return Result.failure(analysis_error, {"step": self.name, "context": context.run_id})

    def _scan_class(self, class_node: cst.ClassDef, module_proposal: ModuleProposal) -> None:
        """Scan a class for fixtures, setup methods, and other metadata."""
        class_name = class_node.name.value

        # Ensure class proposal exists
        if class_name not in module_proposal.class_proposals:
            class_proposal = ClassProposal(class_name=class_name, function_proposals={})
            module_proposal.add_class_proposal(class_proposal)
        else:
            class_proposal = module_proposal.class_proposals[class_name]

        # Collect class-level setup methods
        setup_methods = self._collect_setup_methods(class_node)
        class_proposal.class_setup_methods = setup_methods

        # Collect class-level fixtures
        class_fixtures = self._collect_class_fixtures(class_node)
        class_proposal.class_fixtures = class_fixtures

    def _collect_setup_methods(self, class_node: cst.ClassDef) -> list[str]:
        """Collect setUp and tearDown methods from a class."""
        setup_methods = []
        try:
            for node in class_node.body.body:
                if isinstance(node, cst.FunctionDef):
                    method_name = node.name.value
                    if method_name in ("setUp", "tearDown", "setUpClass", "tearDownClass"):
                        setup_methods.append(method_name)
        except Exception as e:
            self._logger.warning(f"Error collecting setup methods: {e}")
        return setup_methods

    def _collect_class_fixtures(self, class_node: cst.ClassDef) -> list[str]:
        """Collect class-level fixtures."""
        fixtures = []
        try:
            for node in class_node.body.body:
                if isinstance(node, cst.FunctionDef):
                    # Check for pytest fixture decorators on class methods
                    for decorator in node.decorators:
                        if isinstance(decorator.decorator, cst.Call):
                            if isinstance(decorator.decorator.func, cst.Attribute):
                                if (
                                    isinstance(decorator.decorator.func.value, cst.Name)
                                    and decorator.decorator.func.value.value == "pytest"
                                    and decorator.decorator.func.attr.value == "fixture"
                                ):
                                    fixtures.append(node.name.value)
        except Exception as e:
            self._logger.warning(f"Error collecting class fixtures: {e}")
        return fixtures


class FunctionScannerStep(Step[cst.Module, cst.Module]):
    """Scan function-level constructs and detect transformation opportunities."""

    def __init__(self, name: str, event_bus: EventBus) -> None:
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, input_data: cst.Module) -> Result[cst.Module]:
        """Scan functions for subTest loops and other patterns."""
        try:
            self._logger.debug("Scanning function-level constructs")

            # Require the metadata key to be present; synthesize if key exists but value is None
            if "module_proposal" not in context.metadata:
                ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            module_proposal = context.metadata.get("module_proposal")
            if module_proposal is None:
                cst_mod = context.metadata.get("cst_module")
                if cst_mod is not None:
                    module_name = context.source_file or "unknown"
                    module_proposal = ModuleProposal(
                        module_name=module_name,
                        class_proposals={},
                        module_fixtures=[],
                        module_imports=[],
                        top_level_assignments={},
                    )
                    context.metadata["module_proposal"] = module_proposal
                else:
                    ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                    return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            # Scan all functions in the module
            for node in input_data.body:
                if isinstance(node, cst.ClassDef):
                    self._scan_class_functions(node, module_proposal)

            return Result.success(input_data)

        except Exception as e:
            self._logger.error(f"Failed to scan functions: {e}")
            analysis_error = AnalysisStepError(
                f"Failed to scan functions: {e}", "function_scanner", module_name=context.source_file
            )
            return Result.failure(analysis_error, {"step": self.name, "context": context.run_id})

    def _scan_class_functions(self, class_node: cst.ClassDef, module_proposal: ModuleProposal) -> None:
        """Scan functions within a class for transformation opportunities."""
        class_name = class_node.name.value

        # Ensure class proposal exists
        if class_name not in module_proposal.class_proposals:
            class_proposal = ClassProposal(class_name=class_name, function_proposals={})
            module_proposal.add_class_proposal(class_proposal)
        else:
            class_proposal = module_proposal.class_proposals[class_name]

        # Scan each function in the class
        for node in class_node.body.body:
            if isinstance(node, cst.FunctionDef):
                func_proposal = self._analyze_function(node, class_name)
                if func_proposal:
                    class_proposal.add_function_proposal(func_proposal)

    def _analyze_function(self, func_node: cst.FunctionDef, class_name: str) -> FunctionProposal | None:
        """Analyze a function for transformation opportunities."""
        func_name = func_node.name.value

        # Skip non-test methods (those not starting with 'test_')
        if not func_name.startswith("test_"):
            return None

        # Check for subTest loops
        subtest_analysis = self._analyze_subtest_loops(func_node, class_name, func_name)
        if subtest_analysis:
            return subtest_analysis

        # For now, return a basic proposal for test functions without subTest loops
        return FunctionProposal(
            function_name=f"{class_name}.{func_name}",
            recommended_strategy="keep-loop",  # Conservative default
            evidence=["No subTest loops detected"],
        )

    def _analyze_subtest_loops(
        self, func_node: cst.FunctionDef, class_name: str, func_name: str
    ) -> FunctionProposal | None:
        """Analyze function for subTest loop patterns."""
        try:
            body_statements = list(func_node.body.body)

            # Look for For loops in the function body
            for index, stmt in enumerate(body_statements):
                # Skip SimpleStatementLine (which wraps assignments, etc.)
                if isinstance(stmt, cst.SimpleStatementLine):
                    continue

                if not isinstance(stmt, cst.For):
                    continue

                loop_analysis = self._analyze_for_loop(stmt, body_statements, index, class_name, func_name)
                if loop_analysis:
                    return loop_analysis

        except Exception as e:
            self._logger.warning(f"Error analyzing function {func_name}: {e}")
            # Could raise PatternDetectionError here if needed for critical errors

        return None

    def _analyze_for_loop(
        self, for_node: cst.For, body_statements: list, loop_index: int, class_name: str, func_name: str
    ) -> FunctionProposal | None:
        """Analyze a for loop for subTest patterns.

    Note: This function has complex isinstance checks against libcst union
    node types which can trigger mypy false-positives about unreachable
    branches. The implementation uses explicit runtime guards.
    """
        try:
            # Check if this is a subTest loop pattern
            body = for_node.body
            if not isinstance(body, cst.IndentedBlock) or len(body.body) != 1:
                return None

            inner_stmt = body.body[0]
            if not isinstance(inner_stmt, cst.With):
                return None

            if len(inner_stmt.items) != 1:
                return None

            # Check if the with statement contains a subTest call
            with_item = inner_stmt.items[0]
            call = getattr(with_item, "item", None)
            if not isinstance(call, cst.Call):
                return None

            # Check if this is a subTest call
            if not self._is_subtest_call(call):
                return None

            # Extract loop variable names (could be tuple unpacking)
            loop_var_names = self._extract_loop_var_names(for_node.target)
            if not loop_var_names:
                return None

            # For now, use the first variable name
            loop_var_name = loop_var_names[0]

            # Analyze the loop iterable to determine strategy
            strategy, evidence = self._analyze_loop_iterable(
                for_node.iter, body_statements, loop_index, class_name, func_name
            )

            return FunctionProposal(
                function_name=f"{class_name}.{func_name}",
                recommended_strategy=strategy,
                loop_var_name=loop_var_name,
                iterable_origin=self._determine_iterable_origin(for_node.iter),
                evidence=evidence,
            )

        except Exception as e:
            self._logger.warning(f"Error analyzing for loop in {func_name}: {e}")
            # Could raise PatternDetectionError here if needed for critical errors
            return None

    def _is_subtest_call(self, call: cst.Call) -> bool:
        """Check if a call node is a subTest call."""
        try:
            if isinstance(call.func, cst.Attribute):
                if isinstance(call.func.value, cst.Name) and call.func.value.value == "self":
                    if call.func.attr.value == "subTest":
                        return True
        except Exception:
            pass
        return False

    def _extract_loop_var_names(self, target: cst.BaseExpression) -> list[str]:
        """Extract the loop variable names from a target expression."""
        names = []
        try:
            if isinstance(target, cst.Name):
                names.append(target.value)
            elif isinstance(target, cst.Tuple):
                for element in target.elements:
                    # Handle cst.Element wrapper
                    val = getattr(element, "value", None)
                    if isinstance(val, cst.Name):
                        names.append(val.value)
        except Exception:
            pass
        return names

    def _analyze_loop_iterable(
        self, iterable: cst.BaseExpression, body_statements: list, loop_index: int, class_name: str, func_name: str
    ) -> tuple[Literal["parametrize", "subtests", "keep-loop"], list[str]]:
        """Analyze the loop iterable to determine transformation strategy."""
        evidence = []

        # Check for literal lists/tuples (can be parametrized)
        if isinstance(iterable, cst.List | cst.Tuple):
            evidence.append("Found literal list/tuple iterable")
            return "parametrize", evidence

        # Check for simple name references (can be parametrized if not mutated)
        if isinstance(iterable, cst.Name):
            var_name = getattr(iterable, "value", "")
            evidence.append(f"Found name reference: {var_name}")

            # Check if this variable is mutated in the function (accumulator pattern)
            if self._is_variable_mutated(var_name, body_statements, loop_index):
                evidence.append(f"Variable {var_name} is mutated - use subtests")
                return "subtests", evidence
            else:
                evidence.append(f"Variable {var_name} is not mutated - can parametrize")
                return "parametrize", evidence

        # Check for range() calls (can be parametrized)
        if isinstance(iterable, cst.Call):
            func = getattr(iterable, "func", None)
            if isinstance(func, cst.Name) and getattr(func, "value", None) == "range":
                evidence.append("Found range() call - can parametrize")
                return "parametrize", evidence

        # Default to conservative approach
        evidence.append("Unknown iterable type - use subtests")
        return "subtests", evidence

    def _is_variable_mutated(self, var_name: str, body_statements: list, loop_index: int) -> bool:
        """Check if a variable is mutated before the loop."""
        try:
            # Look for mutations of this variable before the loop
            for i in range(loop_index):
                stmt = body_statements[i]

                # Handle SimpleStatementLine wrapper
                if isinstance(stmt, cst.SimpleStatementLine):
                    inner_stmt = stmt.body[0] if stmt.body else None
                else:
                    inner_stmt = stmt

                if isinstance(inner_stmt, cst.Assign):
                    for target in inner_stmt.targets:
                        tgt = getattr(target, "target", None)
                        if isinstance(tgt, cst.Name) and getattr(tgt, "value", None) == var_name:
                            # Check if this is a mutation (reassignment) vs initial assignment
                            # If the variable was already assigned earlier, it's a mutation
                            if self._is_variable_previously_assigned(var_name, body_statements, i):
                                return True
                # Check for augmented assignments (always mutations)
                elif isinstance(inner_stmt, cst.AugAssign):
                    tgt = getattr(inner_stmt, "target", None)
                    if isinstance(tgt, cst.Name) and getattr(tgt, "value", None) == var_name:
                        return True
                # Check for method calls on the variable (like .append())
                elif isinstance(inner_stmt, cst.Expr) and isinstance(getattr(inner_stmt, "value", None), cst.Call):
                    call = inner_stmt.value
                    func = getattr(call, "func", None)
                    if isinstance(func, cst.Attribute):
                        func_val = getattr(func, "value", None)
                        func_attr = getattr(func, "attr", None)
                        if isinstance(func_val, cst.Name) and getattr(func_val, "value", None) == var_name and getattr(func_attr, "value", None) in ("append", "extend", "insert", "update", "pop", "remove"):
                            return True
        except Exception:
            pass
        return False

    def _is_variable_previously_assigned(self, var_name: str, body_statements: list, current_index: int) -> bool:
        """Check if a variable was assigned earlier in the function."""
        try:
            for i in range(current_index):
                stmt = body_statements[i]

                # Handle SimpleStatementLine wrapper
                if isinstance(stmt, cst.SimpleStatementLine):
                    inner_stmt = stmt.body[0] if stmt.body else None
                else:
                    inner_stmt = stmt

                if isinstance(inner_stmt, cst.Assign):
                    for target in inner_stmt.targets:
                        if isinstance(target.target, cst.Name) and target.target.value == var_name:
                            return True
        except Exception:
            pass
        return False

    def _determine_iterable_origin(self, iterable: cst.BaseExpression) -> Literal["literal", "name", "call"] | None:
        """Determine the origin type of an iterable."""
        if isinstance(iterable, cst.List | cst.Tuple):
            return "literal"
        elif isinstance(iterable, cst.Name):
            return "name"
        elif isinstance(iterable, cst.Call):
            return "call"
        return None


class ProposalReconcilerStep(Step[cst.Module, DecisionModel]):
    """Reconcile and aggregate function proposals into final decisions."""

    def __init__(self, name: str, event_bus: EventBus) -> None:
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, input_data: cst.Module) -> Result[DecisionModel]:
        """Reconcile proposals and create final decision model."""
        try:
            self._logger.debug("Reconciling proposals into decision model")

            # Require the metadata key to be present; synthesize if key exists but value is None
            if "module_proposal" not in context.metadata:
                ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            module_proposal = context.metadata.get("module_proposal")
            if module_proposal is None:
                cst_mod = context.metadata.get("cst_module")
                if cst_mod is not None:
                    module_name = context.source_file or "unknown"
                    module_proposal = ModuleProposal(
                        module_name=module_name,
                        class_proposals={},
                        module_fixtures=[],
                        module_imports=[],
                        top_level_assignments={},
                    )
                    context.metadata["module_proposal"] = module_proposal
                else:
                    ctx_error = ContextError("No module proposal found in context", "module_proposal", self.name)
                    return Result.failure(ctx_error, {"step": self.name, "context": context.run_id})

            # Apply reconciliation rules to each class
            for _class_name, class_proposal in module_proposal.class_proposals.items():
                self._reconcile_class_proposals(class_proposal, module_proposal)

            # Create decision model with the reconciled module proposal
            decision_model = DecisionModel(module_proposals={})
            decision_model.add_module_proposal(module_proposal)

            return Result.success(decision_model)

        except Exception as e:
            self._logger.error(f"Failed to reconcile proposals: {e}")
            analysis_error = AnalysisStepError(
                f"Failed to reconcile proposals: {e}", "proposal_reconciler", module_name=context.source_file
            )
            return Result.failure(analysis_error, {"step": self.name, "context": context.run_id})

    def _reconcile_class_proposals(self, class_proposal: ClassProposal, module_proposal: ModuleProposal) -> None:
        """Apply reconciliation rules to function proposals within a class."""
        if not class_proposal.function_proposals:
            return

        # Rule 1: If all functions recommend the same strategy, use it
        strategies = [p.recommended_strategy for p in class_proposal.function_proposals.values()]
        if len(set(strategies)) == 1:
            # All functions agree on the same strategy
            common_strategy = strategies[0]
            for func_proposal in class_proposal.function_proposals.values():
                if func_proposal.recommended_strategy != common_strategy:
                    func_proposal.recommended_strategy = common_strategy
                    func_proposal.evidence.append(f"Aligned to class consensus: {common_strategy}")
            return

        # Rule 2: If there's a mix of parametrize and subtests, keep individual decisions
        # (Don't force all to subtests unless there's a specific reason)
        if "subtests" in strategies and "parametrize" in strategies:
            # For now, keep individual decisions - don't force reconciliation
            # This allows functions that can be parametrized to remain parametrized
            return

        # Rule 3: Check for accumulator patterns that require subtests
        accumulator_functions = [
            name
            for name, proposal in class_proposal.function_proposals.items()
            if proposal.accumulator_mutated or "mutated" in " ".join(proposal.evidence)
        ]

        if accumulator_functions:
            self._apply_accumulator_safety(class_proposal, accumulator_functions)
            return

        # Rule 4: Default to conservative approach - use subtests if any function suggests it
        if "subtests" in strategies:
            self._apply_conservative_approach(class_proposal)

    def _apply_subtests_preference(self, class_proposal: ClassProposal) -> None:
        """Apply rule that prefers subtests when there's a mix of strategies."""
        for _func_name, func_proposal in class_proposal.function_proposals.items():
            if func_proposal.recommended_strategy == "parametrize":
                func_proposal.recommended_strategy = "subtests"
                func_proposal.evidence.append("Changed to subtests due to mixed strategies in class")

    def _apply_accumulator_safety(self, class_proposal: ClassProposal, accumulator_functions: list[str]) -> None:
        """Apply rule that accumulator functions must use subtests."""
        for func_name in accumulator_functions:
            func_proposal = class_proposal.function_proposals[func_name]
            if func_proposal.recommended_strategy != "subtests":
                func_proposal.recommended_strategy = "subtests"
                func_proposal.evidence.append("Changed to subtests due to accumulator pattern")

    def _apply_conservative_approach(self, class_proposal: ClassProposal) -> None:
        """Apply conservative rule - use subtests if any function suggests it."""
        for _func_name, func_proposal in class_proposal.function_proposals.items():
            if func_proposal.recommended_strategy != "subtests":
                func_proposal.recommended_strategy = "subtests"
                func_proposal.evidence.append("Changed to subtests for conservative approach")
