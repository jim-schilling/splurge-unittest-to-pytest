"""Unittest -> pytest transformation shim using libcst.

This module provides a compact, test-focused wrapper around several
smaller transformer modules. The primary entry point used by the
test-suite is :class:`UnittestToPytestCstTransformer`, which applies a
CST-based transformation pass to convert unittest-style tests to
pytest-compatible code. The heavy-weight assertion and string-based
transforms are delegated to helpers in :mod:`assert_transformer` and
other submodules to keep this file concise and focused on orchestration.

The transformer performs the following high-level steps:
- Parse source into a libcst Module and run CST-based passes.
- Record and apply targeted replacements using position metadata.
- Convert lifecycle methods (setUp/tearDown) into pytest fixtures.
- Rewrite unittest assertions and skip decorators to pytest idioms.
- Tidy up unittest.TestCase inheritance and test method names.

This module aims to preserve original formatting where possible and
falls back to conservative string-level transformations when CST-based
rewrites are not applicable.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from ..exceptions import TransformationValidationError
from .assert_transformer import (
    _recursively_rewrite_withs,
    transform_assert_almost_equal,
    transform_assert_count_equal,
    transform_assert_dict_equal,
    transform_assert_equal,
    transform_assert_false,
    transform_assert_greater,
    transform_assert_greater_equal,
    transform_assert_in,
    transform_assert_is,
    transform_assert_is_none,
    transform_assert_is_not,
    transform_assert_is_not_none,
    transform_assert_isinstance,
    transform_assert_less,
    transform_assert_less_equal,
    transform_assert_list_equal,
    transform_assert_multiline_equal,
    transform_assert_not_almost_equal,
    transform_assert_not_equal,
    transform_assert_not_in,
    transform_assert_not_isinstance,
    transform_assert_not_regex,
    transform_assert_raises,
    transform_assert_raises_regex,
    transform_assert_regex,
    transform_assert_set_equal,
    transform_assert_true,
    transform_assert_tuple_equal,
    transform_assert_warns,
    transform_assert_warns_regex,
    transform_caplog_alias_string_fallback,
    transform_fail,
    transform_skip_test,
    wrap_assert_in_block,
)
from .fixture_transformer import (
    create_class_fixture,
    create_instance_fixture,
    create_module_fixture,
)
from .import_transformer import add_pytest_imports, remove_unittest_imports_if_unused
from .skip_transformer import rewrite_skip_decorators
from .subtest_transformer import (
    body_uses_subtests,
    convert_simple_subtests_to_parametrize,
    convert_subtests_in_body,
    ensure_subtests_param,
)
from .transformer_helper import ReplacementApplier, ReplacementRegistry

# mypy: ignore-errors


"""CST-based transformer for unittest to pytest conversion."""


@dataclass
class RegexImportTracker:
    """Track regex import requirements and alias information."""

    needs_pytest_import: bool = False
    needs_re_import: bool = False
    re_alias: str | None = None
    re_search_name: str | None = None


@dataclass
class FixtureCollectionState:
    """Track collected fixture snippets for module, class, and instance scopes."""

    class_setup: list[str] = field(default_factory=list)
    class_teardown: list[str] = field(default_factory=list)
    instance_setup: list[str] = field(default_factory=list)
    instance_teardown: list[str] = field(default_factory=list)
    module_setup: list[str] = field(default_factory=list)
    module_teardown: list[str] = field(default_factory=list)
    per_class_setup: dict[str, list[str]] = field(default_factory=dict)
    per_class_teardown: dict[str, list[str]] = field(default_factory=dict)
    per_class_setup_class: dict[str, list[str]] = field(default_factory=dict)
    per_class_teardown_class: dict[str, list[str]] = field(default_factory=dict)

    def clear_autouse_buffers(self) -> None:
        """Clear collected snippet buffers for module, class, and instance fixtures."""

        self.class_setup.clear()
        self.class_teardown.clear()
        self.instance_setup.clear()
        self.instance_teardown.clear()
        self.module_setup.clear()
        self.module_teardown.clear()

    def clear_per_class_buffers(self) -> None:
        """Clear per-class collected setup and teardown snippets."""

        self.per_class_setup.clear()
        self.per_class_teardown.clear()
        self.per_class_setup_class.clear()
        self.per_class_teardown_class.clear()


class _RemoveUnittestTestCaseBases(cst.CSTTransformer):
    """Remove ``unittest.TestCase`` bases from class definitions."""

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
        new_bases: list[cst.Arg] = []
        changed = False

        for base in updated.bases:
            try:
                if (
                    isinstance(base.value, cst.Attribute)
                    and isinstance(base.value.value, cst.Name)
                    and base.value.value.value == "unittest"
                    and base.value.attr.value == "TestCase"
                ):
                    changed = True
                    continue
            except AttributeError:
                # Malformed CST node, skip this base
                pass

            new_bases.append(base)

        if changed:
            return updated.with_changes(bases=new_bases)

        return updated


class _NormalizeClassBases(cst.CSTTransformer):
    """Normalize class bases so libcst renders them without artifacts."""

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
        try:
            if not updated.bases:
                return cst.ClassDef(name=updated.name, body=updated.body, decorators=updated.decorators)

            rebuilt: list[cst.Arg] = []
            for base in updated.bases:
                try:
                    value = getattr(base, "value", None)
                    if value is None:
                        continue
                    rebuilt.append(cst.Arg(value=value))
                except (AttributeError, TypeError):
                    # Malformed CST node, keep original
                    rebuilt.append(base)

            if not rebuilt:
                return cst.ClassDef(name=updated.name, body=updated.body, decorators=updated.decorators)

            return updated.with_changes(bases=rebuilt)
        except (AttributeError, TypeError, ValueError):
            # CST transformation failed, return unchanged
            return updated


class _NormalizeTestMethodNames(cst.CSTTransformer):
    """Normalize test method names for classes formerly inheriting from unittest."""

    def __init__(
        self,
        unittest_classes: set[str] | None,
        test_prefixes: Sequence[str],
    ) -> None:
        self._stack: list[str] = []
        self._unittest_classes = set(unittest_classes or set())
        prefixes = list(test_prefixes) or ["test"]
        self._test_prefixes: tuple[str, ...] = tuple(prefixes)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._stack.append(node.name.value)

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
        try:
            self._stack.pop()
        except IndexError:
            # Stack underflow, ignore
            pass
        return updated

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        if not self._stack:
            return updated

        current_class = self._stack[-1]
        if current_class not in self._unittest_classes:
            return updated

        name = original.name.value
        for prefix in self._test_prefixes:
            if name.startswith(prefix) and len(name) > len(prefix):
                rest = name[len(prefix) :]
                if rest and rest[0].isupper():
                    return updated.with_changes(name=cst.Name(value=f"{prefix}_{rest}"))

        return updated


class UnittestToPytestCstTransformer(cst.CSTTransformer):
    """CST transformer that converts unittest tests to pytest.

    This class implements a libcst.CSTTransformer that coordinates several
    specialized transformations (assertion rewrites, lifecycle-to-fixture
    conversion, subTest handling, and import cleanup). It is intentionally
    conservative: most changes are implemented as targeted node
    replacements recorded by source position and applied in a second
    pass, which reduces accidental formatting churn.

    Attributes:
        needs_pytest_import (bool): Set when transformations require pytest
            imports (for example when ``pytest.raises`` is emitted).
        needs_re_import (bool): Set when rewritten code needs the ``re``
            module.
        test_prefixes (list[str]): Accepted test method prefixes used when
            normalizing test method names.
        replacement_registry (ReplacementRegistry): Registry used to
            record and later apply node replacements keyed by source span.

    See Also:
        The concrete transformation implementations are provided in the
        sibling modules such as :mod:`assert_transformer`,
        :mod:`fixture_transformer`, and :mod:`subtest_transformer`.
    """

    def __init__(
        self,
        test_prefixes: list[str] | None = None,
        parametrize: bool = True,
        parametrize_include_ids: bool | None = None,
        parametrize_add_annotations: bool | None = None,
        decision_model: Any | None = None,
    ) -> None:
        self._import_tracker = RegexImportTracker()
        self._fixture_state = FixtureCollectionState()
        self.current_class: str | None = None
        # Test method prefixes used for normalization (e.g., ["test", "spec"])
        self.test_prefixes: list[str] = (test_prefixes or ["test"]) or ["test"]
        # Whether to attempt conservative subTest -> parametrize transforms
        self.parametrize = parametrize
        # Parametrize configuration knobs exposed to helper modules
        self.parametrize_include_ids = parametrize_include_ids if parametrize_include_ids is not None else False
        self.parametrize_add_annotations = (
            parametrize_add_annotations if parametrize_add_annotations is not None else False
        )
        # Decision model for enhanced transformation decisions
        self.decision_model = decision_model
        # Replacement registry for two-pass metadata-based replacements
        self.replacement_registry = ReplacementRegistry()
        # Debugging flag to enable verbose internal tracing
        self.debug_trace = True
        # Stack to track current function context during traversal
        self._function_stack: list[str] = []
        # Set of function names that need the pytest 'request' fixture injected
        self._functions_need_request: set[str] = set()
        # Legacy state flags maintained for compatibility with existing helpers/tests
        self.in_setup = False
        self.in_teardown = False
        self.in_setup_class = False
        self.in_teardown_class = False

    @property
    def import_tracker(self) -> RegexImportTracker:
        """Return the import tracker encapsulating pytest and regex flags."""

        return self._import_tracker

    @property
    def fixture_state(self) -> FixtureCollectionState:
        """Return the fixture collection state container."""

        return self._fixture_state

    @property
    def setup_code(self) -> list[str]:
        """Return collected instance-level setup snippets."""

        return self.fixture_state.instance_setup

    @setup_code.setter
    def setup_code(self, value: Sequence[str]) -> None:
        self.fixture_state.instance_setup = list(value)

    @property
    def teardown_code(self) -> list[str]:
        """Return collected instance-level teardown snippets."""

        return self.fixture_state.instance_teardown

    @teardown_code.setter
    def teardown_code(self, value: Sequence[str]) -> None:
        self.fixture_state.instance_teardown = list(value)

    @property
    def setup_class_code(self) -> list[str]:
        """Return collected class-level setup snippets."""

        return self.fixture_state.class_setup

    @setup_class_code.setter
    def setup_class_code(self, value: Sequence[str]) -> None:
        self.fixture_state.class_setup = list(value)

    @property
    def teardown_class_code(self) -> list[str]:
        """Return collected class-level teardown snippets."""

        return self.fixture_state.class_teardown

    @teardown_class_code.setter
    def teardown_class_code(self, value: Sequence[str]) -> None:
        self.fixture_state.class_teardown = list(value)

    @property
    def setup_module_code(self) -> list[str]:
        """Return collected module-level setup snippets."""

        return self.fixture_state.module_setup

    @setup_module_code.setter
    def setup_module_code(self, value: Sequence[str]) -> None:
        self.fixture_state.module_setup = list(value)

    @property
    def teardown_module_code(self) -> list[str]:
        """Return collected module-level teardown snippets."""

        return self.fixture_state.module_teardown

    @teardown_module_code.setter
    def teardown_module_code(self, value: Sequence[str]) -> None:
        self.fixture_state.module_teardown = list(value)

    @property
    def _per_class_setup(self) -> dict[str, list[str]]:
        """Expose per-class instance setup collections for legacy callers."""

        return self.fixture_state.per_class_setup

    @_per_class_setup.setter
    def _per_class_setup(self, value: dict[str, list[str]]) -> None:
        self.fixture_state.per_class_setup = {k: list(v) for k, v in value.items()}

    @property
    def _per_class_teardown(self) -> dict[str, list[str]]:
        """Expose per-class instance teardown collections for legacy callers."""

        return self.fixture_state.per_class_teardown

    @_per_class_teardown.setter
    def _per_class_teardown(self, value: dict[str, list[str]]) -> None:
        self.fixture_state.per_class_teardown = {k: list(v) for k, v in value.items()}

    @property
    def _per_class_setup_class(self) -> dict[str, list[str]]:
        """Expose per-class classmethod setup collections for legacy callers."""

        return self.fixture_state.per_class_setup_class

    @_per_class_setup_class.setter
    def _per_class_setup_class(self, value: dict[str, list[str]]) -> None:
        self.fixture_state.per_class_setup_class = {k: list(v) for k, v in value.items()}

    @property
    def _per_class_teardown_class(self) -> dict[str, list[str]]:
        """Expose per-class classmethod teardown collections for legacy callers."""

        return self.fixture_state.per_class_teardown_class

    @_per_class_teardown_class.setter
    def _per_class_teardown_class(self, value: dict[str, list[str]]) -> None:
        self.fixture_state.per_class_teardown_class = {k: list(v) for k, v in value.items()}

    @property
    def needs_pytest_import(self) -> bool:
        return self._import_tracker.needs_pytest_import

    @needs_pytest_import.setter
    def needs_pytest_import(self, value: bool) -> None:
        self._import_tracker.needs_pytest_import = value

    @property
    def needs_re_import(self) -> bool:
        return self._import_tracker.needs_re_import

    @needs_re_import.setter
    def needs_re_import(self, value: bool) -> None:
        self._import_tracker.needs_re_import = value

    @property
    def re_alias(self) -> str | None:
        return self._import_tracker.re_alias

    @re_alias.setter
    def re_alias(self, value: str | None) -> None:
        self._import_tracker.re_alias = value

    @property
    def re_search_name(self) -> str | None:
        return self._import_tracker.re_search_name

    @re_search_name.setter
    def re_search_name(self, value: str | None) -> None:
        self._import_tracker.re_search_name = value

    # Require PositionProvider metadata so we can record precise source spans
    METADATA_DEPENDENCIES = (PositionProvider,)

    def _compute_module_insert_index(self, body: Sequence[cst.CSTNode]) -> int:
        """Return insertion index after imports and module docstring."""

        insert_index = 0
        for index, node in enumerate(body):
            try:
                if isinstance(node, cst.Import | cst.ImportFrom):
                    insert_index = index + 1
                    continue
                if isinstance(node, cst.SimpleStatementLine) and node.body:
                    first = node.body[0]
                    if isinstance(first, cst.Import | cst.ImportFrom):
                        insert_index = index + 1
                        continue
                    if isinstance(first, cst.Expr) and isinstance(first.value, cst.SimpleString):
                        insert_index = index + 1
                        continue
            except (AttributeError, TypeError, IndexError, cst.ParserSyntaxError):
                # Malformed node, skip and continue
                continue
            break
        return insert_index

    def _should_drop_top_level_node(self, node: cst.CSTNode) -> bool:
        """Determine whether a top-level node should be removed from the module."""

        remove_names = {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule"}

        try:
            fn: cst.FunctionDef | None = None
            if (
                isinstance(node, cst.SimpleStatementLine)
                and len(node.body) == 1
                and isinstance(node.body[0], cst.FunctionDef)
            ):
                fn = node.body[0]
            elif isinstance(node, cst.FunctionDef):
                fn = node

            if fn is not None and fn.name.value in remove_names:
                return True

            if isinstance(node, cst.If):
                test = node.test
                if (
                    isinstance(test, cst.Comparison)
                    and isinstance(test.left, cst.Name)
                    and test.left.value == "__name__"
                ):
                    comparisons = getattr(test, "comparisons", [])
                    if any(
                        isinstance(comp.comparator, cst.SimpleString) and "__main__" in comp.comparator.value
                        for comp in comparisons
                    ):
                        return True

            if isinstance(node, cst.SimpleStatementLine) and node.body:
                first = node.body[0]
                if isinstance(first, cst.Expr) and isinstance(first.value, cst.Call):
                    call = first.value
                    if isinstance(call.func, cst.Attribute) and isinstance(call.func.value, cst.Name):
                        if call.func.attr.value == "main" and call.func.value.value in {"unittest", "pytest"}:
                            return True
        except (AttributeError, TypeError):
            # Malformed node, don't drop it
            return False

        return False

    def _collect_module_fixtures(self) -> list[cst.FunctionDef]:
        """Build module-level fixtures from collected setup/teardown snippets."""

        module_fixtures: list[cst.FunctionDef] = []
        state = self.fixture_state

        setup_class_entries = list(dict.fromkeys(state.class_setup))
        teardown_class_entries = list(dict.fromkeys(state.class_teardown))
        setup_entries = list(dict.fromkeys(state.instance_setup))
        teardown_entries = list(dict.fromkeys(state.instance_teardown))
        setup_module_entries = list(dict.fromkeys(state.module_setup))
        teardown_module_entries = list(dict.fromkeys(state.module_teardown))

        try:
            if setup_class_entries or teardown_class_entries:
                class_fixture = create_class_fixture(setup_class_entries, teardown_class_entries)
                module_fixtures.append(class_fixture)
                self.needs_pytest_import = True

            if setup_entries or teardown_entries:
                instance_fixture = create_instance_fixture(setup_entries, teardown_entries)
                module_fixtures.append(instance_fixture)
                self.needs_pytest_import = True

            if setup_module_entries or teardown_module_entries:
                module_fixture = create_module_fixture(setup_module_entries, teardown_module_entries)
                module_fixtures.append(module_fixture)
                self.needs_pytest_import = True
        except (AttributeError, TypeError, ValueError):
            # Fixture creation failed, skip fixtures
            pass
        finally:
            state.clear_autouse_buffers()

        return module_fixtures

    def _rebuild_class_def(
        self,
        node: cst.ClassDef,
        remove_names: set[str] | None = None,
    ) -> cst.ClassDef:
        """Rebuild a class body while injecting fixtures and removing lifecycle methods."""

        if not isinstance(node.body, cst.IndentedBlock):
            return node

        names_to_remove = remove_names or {
            "setUp",
            "tearDown",
            "setUpClass",
            "tearDownClass",
            "setUpModule",
            "tearDownModule",
        }

        try:
            class_body_items: list[cst.BaseStatement] = []
            body_statements = list(node.body.body)

            # Preserve leading docstring if present.
            idx = 0
            if body_statements and isinstance(body_statements[0], cst.SimpleStatementLine):
                first_stmt = body_statements[0]
                if (
                    len(first_stmt.body) == 1
                    and isinstance(first_stmt.body[0], cst.Expr)
                    and isinstance(first_stmt.body[0].value, cst.SimpleString)
                ):
                    class_body_items.append(first_stmt)
                    idx = 1

            cls_name = node.name.value

            try:
                state = self.fixture_state
                if cls_name in state.per_class_setup_class or cls_name in state.per_class_teardown_class:
                    setup_cls = list(dict.fromkeys(state.per_class_setup_class.get(cls_name, [])))
                    teardown_cls = list(dict.fromkeys(state.per_class_teardown_class.get(cls_name, [])))
                    if setup_cls or teardown_cls:
                        class_fixture = create_class_fixture(setup_cls, teardown_cls)
                        class_body_items.append(class_fixture)
                        self.needs_pytest_import = True

                if cls_name in state.per_class_setup or cls_name in state.per_class_teardown:
                    setup_inst = list(dict.fromkeys(state.per_class_setup.get(cls_name, [])))
                    teardown_inst = list(dict.fromkeys(state.per_class_teardown.get(cls_name, [])))
                    if setup_inst or teardown_inst:
                        instance_fixture = create_instance_fixture(setup_inst, teardown_inst)
                        class_body_items.append(instance_fixture)
                        self.needs_pytest_import = True
            except (AttributeError, TypeError, ValueError):
                # Ignore fixture generation errors and fall back to original statements.
                pass

            for stmt in body_statements[idx:]:
                fn: cst.FunctionDef | None = None
                if (
                    isinstance(stmt, cst.SimpleStatementLine)
                    and len(stmt.body) == 1
                    and isinstance(stmt.body[0], cst.FunctionDef)
                ):
                    fn = stmt.body[0]
                elif isinstance(stmt, cst.FunctionDef):
                    fn = stmt

                if fn is not None and fn.name.value in names_to_remove:
                    continue

                class_body_items.append(stmt)

            return node.with_changes(body=node.body.with_changes(body=class_body_items))
        except (AttributeError, TypeError, ValueError):
            # CST transformation failed, return unchanged
            return node

    def _wrap_top_level_asserts(self, nodes: Sequence[cst.CSTNode]) -> list[cst.CSTNode]:
        """Apply `wrap_assert_in_block` to non-class/function top-level statements."""

        rewritten: list[cst.CSTNode] = []

        for node in nodes:
            if isinstance(node, cst.ClassDef | cst.FunctionDef):
                rewritten.append(node)
                continue

            try:
                wrapped_nodes = wrap_assert_in_block([node])
                rewritten.extend(wrapped_nodes)
            except (AttributeError, TypeError, ValueError):
                # Assert wrapping failed, keep original
                rewritten.append(node)

        return rewritten

    def _rewrite_function_decorators(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Rewrite unittest skip decorators and flag pytest import usage."""

        try:
            original_decorators = list(node.decorators or [])
            new_decorators = rewrite_skip_decorators(original_decorators)
            if new_decorators is not None and new_decorators is not original_decorators:
                self.needs_pytest_import = True
            return node.with_changes(decorators=new_decorators)
        except (AttributeError, TypeError, ValueError):
            # Decorator rewriting failed, return unchanged
            return node

    def _convert_simple_subtests(
        self,
        original_node: cst.FunctionDef,
        node: cst.FunctionDef,
    ) -> tuple[cst.FunctionDef, list[cst.CSTNode]]:
        """Handle parametrize conversion and subTest rewrites for a function body."""

        try:
            current_node = node
            function_name = original_node.name.value

            # Use decision model for transformation guidance (always available)
            if self.decision_model:
                decision = self._get_function_decision(function_name)
                if decision:
                    current_node = self._apply_decision_model_transformation(original_node, current_node, decision)
                else:
                    # No decision for this function, fall back to current logic
                    if getattr(self, "parametrize", False):
                        decorated_node = convert_simple_subtests_to_parametrize(original_node, current_node, self)
                        if decorated_node is not None:
                            current_node = decorated_node
            else:
                # Fallback if decision model is somehow not available (shouldn't happen)
                if getattr(self, "parametrize", False):
                    decorated_node = convert_simple_subtests_to_parametrize(original_node, current_node, self)
                    if decorated_node is not None:
                        current_node = decorated_node

            body_with_subtests = convert_subtests_in_body(current_node.body.body)
            if body_uses_subtests(body_with_subtests):
                current_node = ensure_subtests_param(current_node)

            return current_node, body_with_subtests
        except (AttributeError, TypeError, ValueError):
            # Subtest conversion failed, return original
            return node, list(getattr(node.body, "body", []))

    def _get_function_decision(self, function_name: str) -> Any | None:
        """Get transformation decision for a specific function."""
        if not self.decision_model or not self.current_class:
            return None

        try:
            # Navigate through decision model hierarchy: Module -> Class -> Function
            module_proposals = getattr(self.decision_model, "module_proposals", {})
            if not module_proposals:
                return None

            # For simplicity, assume we're working with a single module
            # In a more complete implementation, we'd need to determine the current module
            module_name = next(iter(module_proposals.keys())) if module_proposals else None
            if not module_name:
                return None

            module_proposal = module_proposals.get(module_name)
            if not module_proposal:
                return None

            class_proposals = getattr(module_proposal, "class_proposals", {})
            class_proposal = class_proposals.get(self.current_class)
            if not class_proposal:
                return None

            function_proposals = getattr(class_proposal, "function_proposals", {})
            return function_proposals.get(function_name)
        except (AttributeError, TypeError, KeyError):
            # Decision model access failed
            return None

    def _apply_decision_model_transformation(
        self,
        original_node: cst.FunctionDef,
        node: cst.FunctionDef,
        decision: Any,
    ) -> cst.FunctionDef:
        """Apply transformation based on decision model recommendation."""
        try:
            strategy = getattr(decision, "recommended_strategy", None)
            if not strategy:
                return node

            if strategy == "parametrize":
                # Use existing parametrize helper
                parametrized = convert_simple_subtests_to_parametrize(original_node, node, self)
                return parametrized if parametrized is not None else node
            elif strategy == "subtests":
                # Ensure subtests fixture and convert subTest calls
                body_with_subtests = convert_subtests_in_body(node.body.body)
                if body_uses_subtests(body_with_subtests):
                    return ensure_subtests_param(node)
                return node
            else:  # 'keep-loop' or unknown strategy
                # Keep the original loop structure
                return node
        except (AttributeError, TypeError, ValueError):
            return node

    def _ensure_fixture_parameters(
        self,
        function_name: str,
        node: cst.FunctionDef,
        body_statements: Sequence[cst.CSTNode],
    ) -> cst.FunctionDef:
        """Ensure request fixture parameter is present when required and inspect caplog usage."""

        result_node = node
        try:
            if function_name in self._functions_need_request:
                params = list(result_node.params.params)
                if not any(isinstance(param.name, cst.Name) and param.name.value == "request" for param in params):
                    params.append(cst.Param(name=cst.Name(value="request")))
                    result_node = result_node.with_changes(params=result_node.params.with_changes(params=params))

            # Detection for caplog usage is retained for parity with previous behavior.
            if self._uses_caplog_at_level(body_statements):
                params = list(result_node.params.params)
                if not any(isinstance(param.name, cst.Name) and param.name.value == "caplog" for param in params):
                    params.append(cst.Param(name=cst.Name(value="caplog")))
                    result_node = result_node.with_changes(params=result_node.params.with_changes(params=params))
        except (AttributeError, TypeError, ValueError):
            return node

        return result_node

    def _uses_caplog_at_level(self, statements: Sequence[cst.CSTNode]) -> bool:
        """Detect `caplog.at_level` usage within the provided statements."""
        try:

            def walk(node: cst.CSTNode) -> bool:
                # Check current node for a caplog.at_level with-call
                if isinstance(node, cst.With):
                    for item in node.items:
                        ctx = getattr(item, "item", None)
                        if isinstance(ctx, cst.Call) and isinstance(ctx.func, cst.Attribute):
                            attr = ctx.func
                            if (
                                isinstance(attr.value, cst.Name)
                                and attr.value.value == "caplog"
                                and isinstance(attr.attr, cst.Name)
                                and attr.attr.value == "at_level"
                            ):
                                return True
                    # Recurse into the with-body
                    for stmt in getattr(node.body, "body", []):
                        if walk(stmt):
                            return True

                # Recurse into common container attributes (body, orelse, finalbody, handlers)
                for child_name in ("body", "orelse", "finalbody", "handlers"):
                    child = getattr(node, child_name, None)
                    if isinstance(child, cst.IndentedBlock):
                        for stmt in getattr(child, "body", []):
                            if walk(stmt):
                                return True
                    elif isinstance(child, list):
                        for stmt in child:
                            if isinstance(stmt, cst.CSTNode) and walk(stmt):
                                return True

                return False

            for stmt in statements:
                if walk(stmt):
                    return True
            return False
        except (AttributeError, TypeError, ValueError):
            return False

    def _apply_recursive_with_rewrites(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Apply recursive with-statement rewrites produced by assertion helpers."""

        try:
            from .assert_transformer import _recursively_rewrite_withs

            try:
                rewritten_body = [_recursively_rewrite_withs(stmt) for stmt in getattr(node.body, "body", [])]
                return node.with_changes(body=node.body.with_changes(body=rewritten_body))
            except (AttributeError, TypeError, ValueError):
                return node
        except (AttributeError, TypeError, ValueError):
            return node

    def _parse_to_module(self, code: str) -> cst.Module:
        """Parse raw source text into a :class:`libcst.Module`."""

        return cst.parse_module(code)

    def _visit_with_metadata(self, module: cst.Module) -> cst.Module:
        """Execute the transformer with metadata support enabled."""

        wrapper = MetadataWrapper(module)
        return wrapper.visit(self)

    def _apply_recorded_replacements(self, module: cst.Module) -> cst.Module:
        """Apply recorded replacements when present, otherwise return the module unchanged."""

        if not self.replacement_registry.replacements:
            return module

        try:
            wrapper = MetadataWrapper(module)
            return wrapper.visit(ReplacementApplier(self.replacement_registry))
        except (AttributeError, TypeError, ValueError):
            return module

    def _apply_recursive_with_cleanup(self, module: cst.Module) -> cst.Module:
        """Apply recursive with-statement rewrites across the module body."""

        try:
            rewritten_body: list[cst.CSTNode] = []
            for node in module.body:
                if isinstance(node, cst.FunctionDef):
                    rewritten_body.append(self._apply_recursive_with_rewrites(node))
                    continue

                if isinstance(node, cst.ClassDef):
                    class_body: list[cst.BaseStatement] = []
                    for stmt in node.body.body:
                        if isinstance(stmt, cst.FunctionDef):
                            class_body.append(self._apply_recursive_with_rewrites(stmt))
                        else:
                            try:
                                class_body.append(_recursively_rewrite_withs(stmt))
                            except (AttributeError, TypeError, ValueError):
                                class_body.append(stmt)
                    rewritten_body.append(node.with_changes(body=node.body.with_changes(body=class_body)))
                    continue

                try:
                    rewritten_body.append(_recursively_rewrite_withs(node))
                except (AttributeError, TypeError, ValueError):
                    rewritten_body.append(node)

            return module.with_changes(body=rewritten_body)
        except (AttributeError, TypeError, ValueError):
            return module

    def _finalize_transformed_code(self, code: str) -> str:
        """Run post-processing passes and validate the transformed source."""

        # NOTE: The earlier conservative safety-net pass that rewrote With-items
        # has been removed in favor of targeted helpers. This method now focuses
        # solely on the final string-level cleanup and validation.

        transformed_code = self._transform_unittest_inheritance(code)

        transformed_code = add_pytest_imports(transformed_code, transformer=self)

        # Targeted post-pass for remaining caplog alias usages.
        try:
            transformed_code = transform_caplog_alias_string_fallback(transformed_code)
        except (AttributeError, TypeError, ValueError):
            pass

        # Conservative string-level fallback for any remaining assertRaises-style contexts.
        try:
            import re

            transformed_code = re.sub(r"with\s+self\.assertRaisesRegex\s*\(", "with pytest.raises(", transformed_code)
            transformed_code = re.sub(r"with\s+self\.assertRaises\s*\(", "with pytest.raises(", transformed_code)
        except (AttributeError, TypeError, ValueError):
            pass

        transformed_code = remove_unittest_imports_if_unused(transformed_code)

        try:
            self._parse_to_module(transformed_code)
        except Exception as validation_error:
            raise TransformationValidationError(str(validation_error)) from validation_error

        return transformed_code

    def _run_inheritance_cleanup(
        self,
        module: cst.Module,
        unittest_classes: set[str] | None,
    ) -> cst.Module:
        """Run the staged inheritance cleanup pipeline on the provided module."""

        transformers: tuple[cst.CSTTransformer, ...] = (
            _RemoveUnittestTestCaseBases(),
            _NormalizeClassBases(),
            _NormalizeTestMethodNames(
                unittest_classes=unittest_classes or set(),
                test_prefixes=self.test_prefixes,
            ),
        )

        cleaned_module = module
        for transformer in transformers:
            try:
                cleaned_module = cleaned_module.visit(transformer)
            except (AttributeError, TypeError, ValueError):
                return cleaned_module

        return cleaned_module

    def record_replacement(self, old_node: cst.CSTNode, new_node: cst.CSTNode) -> None:
        """Record a planned replacement keyed by the original node's position.

        The transformer records replacements using the :class:`PositionProvider`
        metadata so that multiple, independent passes can safely schedule
        modifications without clobbering one another.

        Args:
            old_node: The original CST node to replace.
            new_node: The replacement CST node.

        Returns:
            None. Failures to obtain position metadata are ignored to keep
            the transformer conservative.
        """
        try:
            pos = self.get_metadata(PositionProvider, old_node)
            self.replacement_registry.record(pos, new_node)
            # recorded replacement (silent)
        except (AttributeError, TypeError, ValueError):
            # If metadata isn't available for some reason, skip recording
            pass

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Inspect a class definition and mark unittest.TestCase subclasses.

        If the class inherits from ``unittest.TestCase`` the transformer
        records that fact (used later to adjust method names and insert
        class-scoped fixtures) and sets flags indicating pytest imports
        are required.

        Args:
            node: The :class:`libcst.ClassDef` node being visited.

        Returns:
            None. This method only updates transformer internal state.
        """
        self.current_class = node.name.value

        # Check for unittest.TestCase inheritance
        if not hasattr(self, "_unittest_classes"):
            self._unittest_classes = set()

        for base in node.bases:
            if isinstance(base.value, cst.Attribute):
                if (
                    isinstance(base.value.value, cst.Name)
                    and base.value.value.value == "unittest"
                    and base.value.attr.value == "TestCase"
                ):
                    self.needs_pytest_import = True
                    try:
                        self._unittest_classes.add(node.name.value)
                    except (AttributeError, TypeError, ValueError):
                        pass
                    # Mark this class for transformation
                    break
        return None  # Continue traversal

    # rewrite_skip_decorators moved to transformers.skip_transformer.rewrite_skip_decorators

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Finalize module-level transformations and insert module fixtures.

        This method runs after the module has been traversed and is
        responsible for inserting an autouse module-scoped fixture when
        ``setUpModule``/``tearDownModule`` code was detected. It also
        removes converted lifecycle functions from the top-level body so
        they do not remain as dead code.

        Args:
            original_node: The original :class:`libcst.Module` node.
            updated_node: The module node after inner transformations.

        Returns:
            A possibly modified :class:`libcst.Module` with inserted
            fixtures and lifecycle methods removed.
        """
        new_body = list(updated_node.body)

        # Determine insertion index after imports and module docstring
        insert_index = self._compute_module_insert_index(new_body)

        cleaned_body: list[cst.CSTNode] = []
        remove_names = {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule"}

        # Iterate through top-level nodes; for ClassDefs, insert per-class fixtures and remove original methods
        # When encountering an if __name__ == '__main__' guard that contains
        # only a call to unittest.main(), we will drop the entire guard and
        # not emit any top-level pytest.main() call. If the guard contains
        # other statements in addition to unittest.main(), we replace the
        # inner call with pytest.main(...) and keep the guard.
        for node in new_body:
            if self._should_drop_top_level_node(node):
                continue

            if isinstance(node, cst.ClassDef):
                cleaned_body.append(self._rebuild_class_def(node, remove_names))
            else:
                cleaned_body.append(node)

        # Insert module-level fixtures (collected outside classes) after imports/docstring
        module_fixtures = self._collect_module_fixtures()

        # Clear per-class collected code now that we've inserted fixtures
        self.fixture_state.clear_per_class_buffers()

        # Build final body with module-level fixtures inserted at insert_index
        final_body: list[cst.CSTNode] = []
        for i, node in enumerate(cleaned_body):
            if i == insert_index and module_fixtures:
                for mf in module_fixtures:
                    final_body.append(mf)
            final_body.append(node)

        # If insert_index is at end, append fixtures now
        if insert_index >= len(cleaned_body) and module_fixtures:
            for mf in module_fixtures:
                final_body.append(mf)

        # Note: we intentionally do not append a top-level pytest.main() call
        # for modules where the original `if __name__ == '__main__'` guard only
        # contained `unittest.main()`. Those guards are dropped to avoid
        # emitting a runtime test runner invocation in the transformed module.

        # CST-level post-processing: handle top-level `self.assertLogs`/`self.assertNoLogs`
        # occurrences by running the same helper used for function bodies. This
        # moves that behavior from the string-based fallback into the CST pass
        # so top-level logging assertions are preserved structurally.
        final_body = self._wrap_top_level_asserts(final_body)

        return updated_node.with_changes(body=final_body)

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Perform function-level rewrites and inject required fixtures.

        This method applies several function-scoped rewrites in sequence:
        - Convert simple for+subTest patterns to ``pytest.mark.parametrize`` when
          the transformer was configured to do so.
        - Convert ``self.subTest`` context managers to the pytest-subtests
          style via :func:`convert_subtests_in_body`.
        - Wrap ``assertLogs``/``assertNoLogs`` usages into the appropriate
          caplog helpers using :func:`wrap_assert_in_block`.

        If any transform introduces usage of fixtures like ``request`` or
        ``caplog``, this method ensures the function signature includes
        those parameters (unless intentionally omitted).

        Args:
            original_node: The original :class:`libcst.FunctionDef` node.
            updated_node: The function node after inner transformations.

        Returns:
            A :class:`libcst.FunctionDef` updated with rewritten body,
            decorators, and possibly augmented parameters.
        """
        func_name = original_node.name.value
        node = updated_node
        body_statements: list[cst.CSTNode] = list(getattr(node.body, "body", []))

        try:
            node = self._rewrite_function_decorators(node)
            node, body_statements = self._convert_simple_subtests(original_node, node)
            try:
                wrapped_body = wrap_assert_in_block(body_statements)
            except (AttributeError, TypeError, ValueError):
                wrapped_body = body_statements
            node = node.with_changes(body=node.body.with_changes(body=wrapped_body))
        except (AttributeError, TypeError, ValueError):
            wrapped_body = list(getattr(node.body, "body", []))
            node = node.with_changes(body=node.body.with_changes(body=wrapped_body))

        node = self._ensure_fixture_parameters(func_name, node, wrapped_body)
        node = self._apply_recursive_with_rewrites(node)

        try:
            if body_uses_subtests(getattr(node.body, "body", [])):
                node = ensure_subtests_param(node)
        except (AttributeError, TypeError, ValueError):
            pass

        # Pop function stack if we tracked it
        if self._function_stack:
            try:
                self._function_stack.pop()
            except (AttributeError, TypeError, ValueError):
                pass

        return node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit function definitions to track setUp/tearDown methods."""
        # Track function stack entry so leave_Call can know the enclosing function
        try:
            self._function_stack.append(node.name.value)
        except (AttributeError, TypeError, ValueError):
            pass
        name = node.name.value
        # Decide whether we're inside a class; if so, record per-class; otherwise module-level
        cls = self.current_class
        state = self.fixture_state
        if name == "setUp":
            if cls:
                buffer = state.per_class_setup.setdefault(cls, [])
                self._extract_method_body(node, buffer)
            else:
                self._extract_method_body(node, state.instance_setup)
        elif name == "tearDown":
            if cls:
                buffer = state.per_class_teardown.setdefault(cls, [])
                self._extract_method_body(node, buffer)
            else:
                self._extract_method_body(node, state.instance_teardown)
        elif name == "setUpClass":
            if cls:
                buffer = state.per_class_setup_class.setdefault(cls, [])
                self._extract_method_body(node, buffer)
            else:
                self._extract_method_body(node, state.class_setup)
        elif name == "tearDownClass":
            if cls:
                buffer = state.per_class_teardown_class.setdefault(cls, [])
                self._extract_method_body(node, buffer)
            else:
                self._extract_method_body(node, state.class_teardown)
        elif name == "setUpModule":
            self._extract_method_body(node, state.module_setup)
        elif name == "tearDownModule":
            self._extract_method_body(node, state.module_teardown)

    def _extract_method_body(self, node: cst.FunctionDef, target_list: list[str]) -> None:
        """Serialize statements from a function body into strings.

        The transformer extracts each top-level statement within the
        provided function and appends a generated code string to
        ``target_list``. Compound statements (``if``, ``with``, etc.) are
        preserved by generating a single-statement :class:`libcst.Module`
        containing that statement and appending its rendered code. This
        behavior is used by the fixture conversion helpers which expect
        ready-to-insert source fragments.

        Args:
            node: The function node whose body should be inspected.
            target_list: A list to which serialized statement strings will
                be appended.

        Returns:
            None. Failures to render a statement are ignored; in very
            conservative cases the statement's type name may be appended
            instead.
        """
        if node.body.body:
            for stmt in node.body.body:
                # Preserve any statement (SimpleStatementLine, If, With, etc.) by
                # generating a Module containing that single statement and appending
                # its generated code. This keeps compound statements like `if`
                # blocks intact when we later create fixtures.
                try:
                    stmt_module = cst.Module(body=[stmt])
                    target_list.append(stmt_module.code.strip())
                except (AttributeError, TypeError, ValueError):
                    # Fallback: try to stringify the node or skip if generation fails
                    try:
                        target_list.append(str(type(stmt).__name__))
                    except (AttributeError, TypeError, ValueError):
                        pass

    # Fixture string-based fallback moved to transformers.fixture_transformer.transform_fixtures_string_based

    def visit_Call(self, node: cst.Call) -> bool | None:
        """Detect calls requiring pytest imports or other special handling.

        Currently this visitor looks for uses of ``pytest.raises`` expressed
        as attribute calls (``pytest.raises(...)``). If found, the
        transformer records that pytest imports will be necessary.

        Args:
            node: The :class:`libcst.Call` node being visited.

        Returns:
            True to continue traversal; ``None`` would stop traversal of
            this subtree.
        """
        # Handle pytest.raises calls by setting the needs_pytest_import flag
        if isinstance(node.func, cst.Attribute):
            if isinstance(node.func.value, cst.Name) and node.func.value.value == "pytest":
                if node.func.attr.value == "raises":
                    self.needs_pytest_import = True
        return True  # Continue traversal

    def visit_Import(self, node: cst.Import) -> bool | None:
        """Capture top-level ``import`` statements for modules we care about.

        The transformer currently tracks whether the module imports ``re``
        and captures any alias (for example ``import re as r``) so that
        later transformed code can prefer the existing local name.

        Args:
            node: The :class:`libcst.Import` node being visited.

        Returns:
            True to continue traversal.
        """
        for alias in node.names:
            # alias.name can be a dotted name but for 're' it's a simple Name
            if isinstance(alias.name, cst.Name) and alias.name.value == "re":
                if alias.asname and isinstance(alias.asname.name, cst.Name):
                    self.re_alias = alias.asname.name.value
                else:
                    self.re_alias = "re"
        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:
        """Capture ``from ... import ...`` forms for modules we care about.

        Specifically, this visitor recognizes ``from re import search``
        (with optional alias) and stores the local name so rewritten tests
        can call ``search(...)`` instead of ``re.search(...)`` when the
        original module used the former form.

        Args:
            node: The :class:`libcst.ImportFrom` node being visited.

        Returns:
            True to continue traversal.
        """
        if isinstance(node.module, cst.Name) and node.module.value == "re":
            # node.names can be an ImportStar or a sequence of ImportAlias; guard accordingly
            if isinstance(node.names, cst.ImportStar):
                return True
            # mypy doesn't narrow the union enough to allow iteration in some versions
            for alias in node.names:
                if isinstance(alias, cst.ImportAlias) and isinstance(alias.name, cst.Name):
                    if alias.name.value == "search":
                        if alias.asname and isinstance(alias.asname.name, cst.Name):
                            self.re_search_name = alias.asname.name.value
                        else:
                            self.re_search_name = "search"
        return True

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        """Transform supported ``self.assert*`` calls into pytest equivalents.

        This method handles attribute calls on ``self`` or ``cls`` and
        dispatches to the specific assertion transform helpers defined in
        :mod:`assert_transformer`. Transformations may:

        - Return an expression-level replacement (safe to return directly).
        - Return a statement-level replacement (these are recorded via
          :meth:`record_replacement` and applied in a later pass).

        Side Effects:
            May set ``needs_pytest_import`` or ``needs_re_import`` when a
            transform emits constructs that require those imports.

        Args:
            original_node: The original :class:`libcst.Call` node.
            updated_node: The call node after inner transforms.

        Returns:
            A :class:`libcst.BaseExpression` representing the transformed
            call or the original node when no transform applies.
        """
        # We're only interested in attribute calls on `self` or `cls` (e.g., self.assertEqual(...) or cls.assertEqual(...))
        if isinstance(updated_node.func, cst.Attribute) and isinstance(updated_node.func.value, cst.Name):
            owner = updated_node.func.value.value
            if owner in {"self", "cls"}:
                method_name = updated_node.func.attr.value

                # Map known unittest assert method names to the extracted transform functions
                mapping = {
                    "assertEqual": transform_assert_equal,
                    "assertEquals": transform_assert_equal,
                    "assertNotEqual": transform_assert_not_equal,
                    "assertNotEquals": transform_assert_not_equal,
                    "assertTrue": transform_assert_true,
                    "assertIsTrue": transform_assert_true,
                    "assertFalse": transform_assert_false,
                    "assertIsFalse": transform_assert_false,
                    "assertIs": transform_assert_is,
                    "assertIsNot": transform_assert_is_not,
                    "assertIn": transform_assert_in,
                    "assertNotIn": transform_assert_not_in,
                    "assertIsInstance": transform_assert_isinstance,
                    "assertNotIsInstance": transform_assert_not_isinstance,
                    "assertDictEqual": transform_assert_dict_equal,
                    "assertDictEquals": transform_assert_dict_equal,
                    "assertListEqual": transform_assert_list_equal,
                    "assertListEquals": transform_assert_list_equal,
                    "assertSetEqual": transform_assert_set_equal,
                    "assertSetEquals": transform_assert_set_equal,
                    "assertTupleEqual": transform_assert_tuple_equal,
                    "assertTupleEquals": transform_assert_tuple_equal,
                    "assertCountEqual": transform_assert_count_equal,
                    "assertSequenceEqual": transform_assert_equal,
                    "skipTest": transform_skip_test,
                    "fail": transform_fail,
                    "assertMultiLineEqual": transform_assert_multiline_equal,
                    "assertIsNone": transform_assert_is_none,
                    "assertIsNotNone": transform_assert_is_not_none,
                    # raises / regex handled with lambdas so we can pass transformer context when needed
                    "assertRaises": transform_assert_raises,
                    "assertRaisesRegex": transform_assert_raises_regex,
                    # warning assertions
                    "assertWarns": transform_assert_warns,
                    "assertWarnsRegex": transform_assert_warns_regex,
                    # numeric comparisons
                    "assertGreater": transform_assert_greater,
                    "assertGreaterEqual": transform_assert_greater_equal,
                    "assertLess": transform_assert_less,
                    "assertLessEqual": transform_assert_less_equal,
                    "assertAlmostEqual": transform_assert_almost_equal,
                    "assertNotAlmostEqual": transform_assert_not_almost_equal,
                    # assertLogs/assertNoLogs handled by wrap_assert_logs_in_block
                    "assertRegex": lambda node: transform_assert_regex(
                        node, re_alias=self.re_alias, re_search_name=self.re_search_name
                    ),
                    "assertNotRegex": lambda node: transform_assert_not_regex(
                        node, re_alias=self.re_alias, re_search_name=self.re_search_name
                    ),
                }

                if method_name in mapping:
                    try:
                        new_node = mapping[method_name](updated_node)
                        # If we transformed to pytest.raises, ensure import is tracked
                        if method_name in {"assertRaises", "assertRaisesRegex"}:
                            self.needs_pytest_import = True
                        # If we transformed regex assertions, note that we need `re`
                        if method_name in {"assertRegex", "assertNotRegex"}:
                            self.needs_re_import = True
                        # new_node may be a statement (e.g., cst.Assert) or an expression.
                        # If it's a statement, record a replacement to apply in a second pass
                        # keyed by source position. Otherwise return the expression.
                        if isinstance(new_node, cst.BaseStatement):
                            # schedule replacement and keep the Call expression intact for now
                            self.record_replacement(original_node, new_node)
                            return updated_node
                        # expression-level replacement is safe to return
                        return new_node  # type: ignore[return-value]
                    except (AttributeError, TypeError, ValueError):
                        # On any transformation error, fall back to the original node
                        return updated_node

                # Note: preserve TestCase API calls like self.id() and self.shortDescription()
                # to maintain compatibility with string-based fallback handling and tests.

        return updated_node

    def visit_Expr(self, node: cst.Expr) -> bool | None:
        """Visit expression statements to detect transformed assertion calls.

        Some assertion transforms produce bare ``assert`` expressions or
        other statement-like forms as call results. This visitor inspects
        expressions that may contain transformed calls so later passes can
        correctly handle them. For now, this method is conservative and
        does not alter the CST in-place.

        Args:
            node: The :class:`libcst.Expr` node being visited.

        Returns:
            True to continue traversal.
        """
        # The value might be a transformed Call, so we need to return a new Expr
        # with the (potentially transformed) value
        if isinstance(node.value, cst.Call):
            # Check if this Call has been transformed
            call = node.value
            if isinstance(call.func, cst.Name) and call.func.value == "assert":
                # This is a transformed assertion, make sure it's properly wrapped
                pass  # For now, we don't modify the CST in place
        return True  # Continue traversal

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool | None:
        """Inspect simple statement lines for transformed assertion expressions.

        When a previously visited Call was transformed into an expression
        that should be a top-level statement (for example an ``assert``),
        this visitor detects that pattern. The implementation remains
        conservative and avoids in-place modifications here.

        Args:
            node: The :class:`libcst.SimpleStatementLine` being visited.

        Returns:
            True to continue traversal.
        """
        # The body might contain transformed expressions, so we need to return a new SimpleStatementLine
        # with the (potentially transformed) body

        # If the body contains an Expr with a transformed Call, make sure it's properly handled
        if len(node.body) > 0 and isinstance(node.body[0], cst.Expr) and isinstance(node.body[0].value, cst.Call):
            call = node.body[0].value
            if isinstance(call.func, cst.Name) and call.func.value == "assert":
                # This contains a transformed assertion
                pass  # For now, we don't modify the CST in place

        return True  # Continue traversal

    def transform_code(self, code: str) -> str:
        """Convert a source string containing unittest-based tests to pytest.

        The method first parses the input into a libcst Module and runs the
        transformer passes. Any recorded position-based replacements are
        applied in a subsequent pass. After CST-based transforms it runs a
        few conservative string-level cleanups (for example caplog alias
        fixes) and removes ``unittest`` imports that are no longer used.

        Args:
            code: The source code to transform.

        Returns:
            The transformed source code on success. If a validation or
            parse error occurs during transformation a comment explaining
            the failure is prepended to the original code and returned.
        """
        try:
            module = self._parse_to_module(code)

            transformed_cst = self._visit_with_metadata(module)

            # Previously we had a conservative post-pass here to catch any
            # remaining `self.assertRaises`/`self.assertRaisesRegex` With-items
            # that were not persisted by the main CST pass. After cleaning up
            # interim debug scaffolding and validating the helper integration
            # we rely on the primary pass to perform these rewrites; retaining
            # a post-pass risks masking real pipeline bugs and causes extra
            # churn. If regressions appear later, reintroduce a focused
            # fallback with tight unit tests guarding it.

            # If we recorded replacements, run a second pass to apply them.
            transformed_cst = self._apply_recorded_replacements(transformed_cst)

            transformed_code = transformed_cst.code

            # Focused final CST pass: apply a lightweight recursive With-item rewrite
            # across top-level statements to catch any remaining context managers.
            transformed_cst = self._apply_recursive_with_cleanup(transformed_cst)
            transformed_code = transformed_cst.code

            transformed_code = self._finalize_transformed_code(transformed_code)

            return transformed_code

        except TransformationValidationError as validation_error:
            error_msg = f"# Transformation validation failed: {str(validation_error)}\n"
            return error_msg + code
        except Exception as error:
            # If CST parsing fails, return original code with comment
            error_msg = f"# CST transformation failed: {str(error)}\n"
            return error_msg + code

    def _transform_unittest_inheritance(self, code: str) -> str:
        """Remove ``unittest.TestCase`` inheritance using libcst and normalize classes.

        This helper performs multiple libcst passes to:

        1. Remove explicit ``unittest.TestCase`` bases from class
           definitions.
        2. Normalize class base rendering to avoid leaving empty
           parentheses or stray commas.
        3. Adjust test method names inside formerly ``unittest.TestCase``
           subclasses (inserting an underscore when a test name like
           ``testSomething`` would be rendered as ``test_Something``).

        Args:
            code: The source code to process.

        Returns:
            The code with unittest inheritance removed and class names
            normalized. If an error occurs the original ``code`` is
            returned unchanged.
        """
        try:
            module = cst.parse_module(code)
        except (AttributeError, TypeError, ValueError):
            return code

        try:
            unittest_classes = set(getattr(self, "_unittest_classes", set()))
        except (AttributeError, TypeError, ValueError):
            unittest_classes = set()

        try:
            cleaned_module = self._run_inheritance_cleanup(module, unittest_classes)
        except (AttributeError, TypeError, ValueError):
            return code

        try:
            return cleaned_module.code
        except (AttributeError, TypeError, ValueError):
            return code
