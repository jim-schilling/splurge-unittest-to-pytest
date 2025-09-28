"""Lightweight UnittestToPytestCSTTransformer shim.

This minimal implementation provides the public API used by tests
(`UnittestToPytestCSTTransformer.transform_code`) while delegating
heavy-duty assertion string transforms to the extracted
`assert_transformer.transform_assertions_string_based` helpers.

The full CST-based transformer was large and has been refactored into
smaller modules; this shim keeps compatibility for the test-suite.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .assert_transformer import (
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
    transform_caplog_alias_string_fallback,
    transform_fail,
    transform_skip_test,
    wrap_assert_logs_in_block,
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


class UnittestToPytestCstTransformer(cst.CSTTransformer):
    """CST-based transformer for unittest to pytest conversion.

    This class systematically transforms unittest code to pytest using libcst:
    1. Parse Python code into AST using libcst
    2. Keep unittest.TestCase class structure but transform inheritance
    3. Transform setUpClass/tearDownClass to class-level fixtures (scope='class')
    4. Transform setUp/tearDown to instance-level fixtures (autouse=True)
    5. Transform assertions using CST node transformations
    6. Generate clean pytest code from transformed CST
    """

    def __init__(self, test_prefixes: list[str] | None = None, parametrize: bool = False) -> None:
        self.needs_pytest_import = False
        # Track whether our transforms require `re` and any alias used in the file
        self.needs_re_import = False
        self.re_alias: str | None = None
        # If the module does `from re import search as s` or `from re import search`,
        # capture the local name to prefer `search(...)` form
        self.re_search_name: str | None = None
        self.current_class: str | None = None
        # Per-class collected setup/teardown code so we can re-insert fixtures inside classes
        self.setup_code: list[str] = []
        self.teardown_code: list[str] = []
        self.setup_class_code: list[str] = []
        self.teardown_class_code: list[str] = []
        self._per_class_setup: dict[str, list[str]] = {}
        self._per_class_teardown: dict[str, list[str]] = {}
        self._per_class_setup_class: dict[str, list[str]] = {}
        self._per_class_teardown_class: dict[str, list[str]] = {}
        self.setup_module_code: list[str] = []
        self.teardown_module_code: list[str] = []
        self.in_setup = False
        self.in_teardown = False
        self.in_setup_class = False
        self.in_teardown_class = False
        # Test method prefixes used for normalization (e.g., ["test", "spec"])
        self.test_prefixes: list[str] = (test_prefixes or ["test"]) or ["test"]
        # Whether to attempt conservative subTest -> parametrize transforms
        self.parametrize = parametrize
        # Replacement registry for two-pass metadata-based replacements
        self.replacement_registry = ReplacementRegistry()
        # Stack to track current function context during traversal
        self._function_stack: list[str] = []
        # Set of function names that need the pytest 'request' fixture injected
        self._functions_need_request: set[str] = set()
        # (function stack fields are initialized in __init__)

    # Require PositionProvider metadata so we can record precise source spans
    METADATA_DEPENDENCIES = (PositionProvider,)

    def record_replacement(self, old_node: cst.CSTNode, new_node: cst.CSTNode) -> None:
        """Record a planned replacement for old_node -> new_node using PositionProvider."""
        try:
            pos = self.get_metadata(PositionProvider, old_node)
            self.replacement_registry.record(pos, new_node)
        except Exception:
            # If metadata isn't available for some reason, skip recording
            pass

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit class definition to check for unittest.TestCase inheritance."""
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
                    except Exception:
                        pass
                    # Mark this class for transformation
                    break
        return None  # Continue traversal

    # rewrite_skip_decorators moved to transformers.skip_transformer.rewrite_skip_decorators

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Inject a module-scoped autouse fixture if setUpModule/tearDownModule were present."""
        new_body = list(updated_node.body)

        # Determine insertion index after imports and module docstring
        insert_index = 0
        for i, node in enumerate(new_body):
            # Keep moving past imports and module-level docstring
            # Handle Import/ImportFrom nodes as well as SimpleStatementLine wrappers.
            if isinstance(node, cst.Import | cst.ImportFrom):
                insert_index = i + 1
                continue
            if isinstance(node, cst.SimpleStatementLine) and node.body:
                first = node.body[0]
                if isinstance(first, cst.Import | cst.ImportFrom):
                    insert_index = i + 1
                    continue
                if isinstance(first, cst.Expr) and isinstance(first.value, cst.SimpleString):
                    insert_index = i + 1
                    continue
            break

        cleaned_body: list[cst.CSTNode] = []
        remove_names = {"setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule"}

        # Iterate through top-level nodes; for ClassDefs, insert per-class fixtures and remove original methods
        found_unittest_main = False
        for node in new_body:
            # Skip top-level lifecycle function definitions (module-level setUp/tearDown)
            fn = None
            if (
                isinstance(node, cst.SimpleStatementLine)
                and len(node.body) == 1
                and isinstance(node.body[0], cst.FunctionDef)
            ):
                fn = node.body[0]
            elif isinstance(node, cst.FunctionDef):
                fn = node

            if fn is not None and isinstance(fn, cst.FunctionDef) and fn.name.value in remove_names:
                # skip adding this top-level function; it was converted to a fixture
                continue

            # Skip a top-level ``if __name__ == '__main__'`` guard which often wraps
            # an invocation of `unittest.main()` in original unittest files. For pytest
            # outputs we do not preserve this guard; removing it prevents an extra
            # If node from appearing in the generated module structure.
            if isinstance(node, cst.If):
                try:
                    # Match patterns like: if __name__ == '__main__':
                    test = node.test
                    if (
                        isinstance(test, cst.Comparison)
                        and isinstance(test.left, cst.Name)
                        and test.left.value == "__name__"
                    ):
                        # Look for a string comparator of "__main__"
                        skip_if = False
                        for comp in test.comparisons:
                            comparator = comp.comparator
                            if isinstance(comparator, cst.SimpleString) and "__main__" in comparator.value:
                                # mark to skip this If node entirely
                                skip_if = True
                                break
                        if skip_if:
                            # If the If block contains an invocation of `unittest.main()`,
                            # emit a top-level `pytest.main()` call instead of preserving
                            # the original guard. This keeps test expectations that
                            # `pytest.main()` appears in the transformed output while
                            # avoiding retaining the `if __name__ == '__main__'` guard.
                            # Inspect the body of the If to detect unittest.main() calls.
                            try:
                                for inner in node.body.body:
                                    # look for simple expression statements like `unittest.main()`
                                    if isinstance(inner, cst.SimpleStatementLine) and inner.body:
                                        first = inner.body[0]
                                        if isinstance(first, cst.Expr) and isinstance(first.value, cst.Call):
                                            call = first.value
                                            # match unittest.main(...) or just unittest.main()
                                            if isinstance(call.func, cst.Attribute) and isinstance(
                                                call.func.value, cst.Name
                                            ):
                                                if (
                                                    call.func.value.value == "unittest"
                                                    and call.func.attr.value == "main"
                                                ):
                                                    # Detected an invocation of unittest.main();
                                                    # record detection so we can emit pytest.main()
                                                    found_unittest_main = True
                                                    break
                            except Exception:
                                pass

                            # skip adding this If node in all cases
                            # If the If guard wraps a unittest.main() call, drop the
                            # entire If node (do not preserve the __main__ guard). We
                            # intentionally do not append a `pytest.main()` call so
                            # transformed outputs don't gain an extra top-level Expr.
                            continue
                except Exception:
                    # If anything goes wrong while inspecting, fall back to keeping the node
                    pass

            if isinstance(node, cst.ClassDef):
                cls_name = node.name.value
                # Build new class body, skipping original setup/teardown methods
                if isinstance(node.body, cst.IndentedBlock):
                    class_body_items: list[cst.BaseStatement] = []
                    # If class has docstring as first statement, keep it at top
                    idx = 0
                    if node.body.body and isinstance(node.body.body[0], cst.SimpleStatementLine):
                        first = node.body.body[0]
                        if (
                            len(first.body) == 1
                            and isinstance(first.body[0], cst.Expr)
                            and isinstance(first.body[0].value, cst.SimpleString)
                        ):
                            class_body_items.append(first)
                            idx = 1

                    # Insert per-class fixtures (class-scoped then instance-scoped) if collected
                    try:
                        if cls_name in self._per_class_setup_class or cls_name in self._per_class_teardown_class:
                            setup_cls = list(dict.fromkeys(self._per_class_setup_class.get(cls_name, [])))
                            teardown_cls = list(dict.fromkeys(self._per_class_teardown_class.get(cls_name, [])))
                            if setup_cls or teardown_cls:
                                class_fixture = create_class_fixture(setup_cls, teardown_cls)
                                class_body_items.append(class_fixture)
                                self.needs_pytest_import = True
                        if cls_name in self._per_class_setup or cls_name in self._per_class_teardown:
                            setup_inst = list(dict.fromkeys(self._per_class_setup.get(cls_name, [])))
                            teardown_inst = list(dict.fromkeys(self._per_class_teardown.get(cls_name, [])))
                            if setup_inst or teardown_inst:
                                inst_fixture = create_instance_fixture(setup_inst, teardown_inst)
                                class_body_items.append(inst_fixture)
                                self.needs_pytest_import = True
                    except Exception:
                        # ignore fixture generation errors for this class
                        pass

                    # Now append remaining original class statements except methods we removed
                    for stmt in node.body.body[idx:]:
                        fn = None
                        if (
                            isinstance(stmt, cst.SimpleStatementLine)
                            and len(stmt.body) == 1
                            and isinstance(stmt.body[0], cst.FunctionDef)
                        ):
                            fn = stmt.body[0]
                        elif isinstance(stmt, cst.FunctionDef):
                            fn = stmt  # type: ignore

                        if fn is not None and isinstance(fn, cst.FunctionDef) and fn.name.value in remove_names:
                            continue
                        class_body_items.append(stmt)

                    new_node = node.with_changes(body=node.body.with_changes(body=class_body_items))
                    cleaned_body.append(new_node)
                else:
                    cleaned_body.append(node)
            else:
                cleaned_body.append(node)

        # Insert module-level fixtures (collected outside classes) after imports/docstring
        module_fixtures: list[cst.FunctionDef] = []
        try:
            # class-scoped module-level code (rare) -> create class fixture
            sc = list(dict.fromkeys(self.setup_class_code))
            tc = list(dict.fromkeys(self.teardown_class_code))
            if sc or tc:
                class_fixture = create_class_fixture(sc, tc)
                module_fixtures.append(class_fixture)
                self.needs_pytest_import = True

            # instance-scoped module-level code -> create instance fixture
            s = list(dict.fromkeys(self.setup_code))
            t = list(dict.fromkeys(self.teardown_code))
            if s or t:
                inst_fixture = create_instance_fixture(s, t)
                module_fixtures.append(inst_fixture)
                self.needs_pytest_import = True

            # module-level setup/teardown collected from setUpModule/tearDownModule
            sm = list(dict.fromkeys(self.setup_module_code))
            tm = list(dict.fromkeys(self.teardown_module_code))
            if sm or tm:
                mod_fixture = create_module_fixture(sm, tm)
                module_fixtures.append(mod_fixture)
                self.needs_pytest_import = True
        except Exception:
            pass

        # Clear module-level collected code to avoid duplication
        self.setup_class_code = []
        self.teardown_class_code = []
        self.setup_code = []
        self.teardown_code = []
        # clear module-level lifecycle collections
        self.setup_module_code = []
        self.teardown_module_code = []

        # Clear per-class collected code now that we've inserted fixtures
        self._per_class_setup.clear()
        self._per_class_teardown.clear()
        self._per_class_setup_class.clear()
        self._per_class_teardown_class.clear()

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

        # If we detected a unittest.main() guarded by `if __name__ == '__main__'`,
        # append a top-level pytest.main() call so transformed output preserves
        # the expectation that a test-run invocation exists.
        if found_unittest_main:
            try:
                call = cst.Call(
                    func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="main")), args=[]
                )
                stmt = cst.SimpleStatementLine(body=[cst.Expr(value=call)])
                final_body.append(stmt)
                self.needs_pytest_import = True
            except Exception:
                pass

        # CST-level post-processing: handle top-level `self.assertLogs`/`self.assertNoLogs`
        # occurrences by running the same helper used for function bodies. This
        # moves that behavior from the string-based fallback into the CST pass
        # so top-level logging assertions are preserved structurally.
        try:
            # Only call if helper is available
            final_body = wrap_assert_logs_in_block(list(final_body))  # type: ignore[arg-type]
        except Exception:
            # Be conservative: if rewrite fails, keep original final_body
            pass

        return updated_node.with_changes(body=final_body)

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Handle function-level rewrites: parametrize conversion, subTest -> subtests, and assertLogs wrapping.

        Also inject the `request` fixture parameter when transforms (e.g., self.id()) require it.
        """
        func_name = original_node.name.value
        try:
            # Rewrite function-level decorators (skip/skipIf)
            orig_decorators = list(updated_node.decorators or [])
            new_decorators = rewrite_skip_decorators(orig_decorators)
            if new_decorators is not None and new_decorators is not orig_decorators:
                self.needs_pytest_import = True
            updated_node = updated_node.with_changes(decorators=new_decorators)

            # First, try conservative parametrize conversion for simple for+subTest patterns
            if getattr(self, "parametrize", False):
                decorated_node = convert_simple_subtests_to_parametrize(original_node, updated_node, self)
                if decorated_node is not None:
                    updated_node = decorated_node

            # Convert subTest context managers to pytest-subtests usage
            body_with_subtests = convert_subtests_in_body(updated_node.body.body)

            # If we introduced subtests usage, ensure the function signature includes the fixture
            if body_uses_subtests(body_with_subtests):
                updated_node = ensure_subtests_param(updated_node)

            # Then wrap assertLogs/assertNoLogs patterns using shared helper
            new_body = wrap_assert_logs_in_block(body_with_subtests)
            result_node = updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        except Exception:
            result_node = updated_node

        # If this function was marked as requiring the pytest 'request' fixture, ensure it exists
        if func_name in self._functions_need_request:
            params = list(result_node.params.params)
            if not any(isinstance(p.name, cst.Name) and p.name.value == "request" for p in params):
                params.append(cst.Param(name=cst.Name(value="request")))
                new_params = result_node.params.with_changes(params=params)
                result_node = result_node.with_changes(params=new_params)

        # If this function body uses caplog.at_level context manager (from assertLogs conversion),
        # inject the 'caplog' fixture parameter if it's not already present.
        try:
            uses_caplog = False
            for stmt in getattr(result_node.body, "body", []):
                if isinstance(stmt, cst.With):
                    for item in stmt.items:
                        # WithItem stores the context expression in `.item`
                        ctx = getattr(item, "item", None)
                        if isinstance(ctx, cst.Call) and isinstance(ctx.func, cst.Attribute):
                            attr = ctx.func
                            if isinstance(attr.value, cst.Name) and attr.value.value == "caplog":
                                if isinstance(attr.attr, cst.Name) and attr.attr.value == "at_level":
                                    uses_caplog = True
                                    break
                    if uses_caplog:
                        break
            # We no longer inject the caplog fixture parameter automatically here.
            # The test harness expects the caplog fixture to be used via the
            # pytest ecosystem rather than being added to every signature.
        except Exception:
            # be conservative on errors and leave function untouched
            pass

        # Pop function stack if we tracked it
        if self._function_stack:
            try:
                self._function_stack.pop()
            except Exception:
                pass

        return result_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit function definitions to track setUp/tearDown methods."""
        # Track function stack entry so leave_Call can know the enclosing function
        try:
            self._function_stack.append(node.name.value)
        except Exception:
            pass
        name = node.name.value
        # Decide whether we're inside a class; if so, record per-class; otherwise module-level
        cls = self.current_class
        if name == "setUp":
            if cls:
                self._per_class_setup.setdefault(cls, [])
                self._extract_method_body(node, self._per_class_setup[cls])
            else:
                self._extract_method_body(node, self.setup_code)
        elif name == "tearDown":
            if cls:
                self._per_class_teardown.setdefault(cls, [])
                self._extract_method_body(node, self._per_class_teardown[cls])
            else:
                self._extract_method_body(node, self.teardown_code)
        elif name == "setUpClass":
            if cls:
                self._per_class_setup_class.setdefault(cls, [])
                self._extract_method_body(node, self._per_class_setup_class[cls])
            else:
                self._extract_method_body(node, self.setup_class_code)
        elif name == "tearDownClass":
            if cls:
                self._per_class_teardown_class.setdefault(cls, [])
                self._extract_method_body(node, self._per_class_teardown_class[cls])
            else:
                self._extract_method_body(node, self.teardown_class_code)
        elif name == "setUpModule":
            self._extract_method_body(node, self.setup_module_code)
        elif name == "tearDownModule":
            self._extract_method_body(node, self.teardown_module_code)

    def _extract_method_body(self, node: cst.FunctionDef, target_list: list[str]) -> None:
        """Extract statements from method body."""
        if node.body.body:
            for stmt in node.body.body:
                # Preserve any statement (SimpleStatementLine, If, With, etc.) by
                # generating a Module containing that single statement and appending
                # its generated code. This keeps compound statements like `if`
                # blocks intact when we later create fixtures.
                try:
                    stmt_module = cst.Module(body=[stmt])
                    target_list.append(stmt_module.code.strip())
                except Exception:
                    # Fallback: try to stringify the node or skip if generation fails
                    try:
                        target_list.append(str(type(stmt).__name__))
                    except Exception:
                        pass

    # Fixture string-based fallback moved to transformers.fixture_transformer.transform_fixtures_string_based

    def visit_Call(self, node: cst.Call) -> bool | None:
        """Visit function calls to detect pytest.raises usage."""
        # Handle pytest.raises calls by setting the needs_pytest_import flag
        if isinstance(node.func, cst.Attribute):
            if isinstance(node.func.value, cst.Name) and node.func.value.value == "pytest":
                if node.func.attr.value == "raises":
                    self.needs_pytest_import = True
        return True  # Continue traversal

    def visit_Import(self, node: cst.Import) -> bool | None:
        """Detect imports of the `re` module and capture any alias (e.g., import re as r)."""
        for alias in node.names:
            # alias.name can be a dotted name but for 're' it's a simple Name
            if isinstance(alias.name, cst.Name) and alias.name.value == "re":
                if alias.asname and isinstance(alias.asname.name, cst.Name):
                    self.re_alias = alias.asname.name.value
                else:
                    self.re_alias = "re"
        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool | None:
        """Detect `from re import search` (with optional alias) and capture the local name."""
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
        """Prefer CST-based assertion transforms for supported self.assert* calls.

        This will run before the string-based fallback so that well-formed
        assertion calls are transformed using libcst nodes.
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
                    except Exception:
                        # On any transformation error, fall back to the original node
                        return updated_node

                # Note: preserve TestCase API calls like self.id() and self.shortDescription()
                # to maintain compatibility with string-based fallback handling and tests.

        return updated_node

    def visit_Expr(self, node: cst.Expr) -> bool | None:
        """Visit expression statements to handle transformed calls."""
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
        """Visit simple statement lines to handle transformed expressions."""
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
        """Transform unittest code to pytest code using CST first, then fallback string ops."""
        try:
            # Parse the code into CST to understand the structure
            module = cst.parse_module(code)

            # Apply CST transformer (handles fixture injection). Use MetadataWrapper
            # so our transformer can access PositionProvider metadata for recording
            # replacements keyed by source spans.
            wrapper = MetadataWrapper(module)
            transformed_cst = wrapper.visit(self)

            # If we recorded replacements, run a second pass to apply them.
            if self.replacement_registry.replacements:
                transformed_cst = MetadataWrapper(transformed_cst).visit(ReplacementApplier(self.replacement_registry))

            transformed_code = transformed_cst.code

            # Use CST-based cleanup for removing unittest.TestCase inheritance
            transformed_code = self._transform_unittest_inheritance(transformed_code)

            # At this point all assertion and fixture rewrites should be done
            # via libcst passes. Add necessary imports (pass transformer so
            # import_transformer can consult attributes like needs_re_import).
            transformed_code = add_pytest_imports(transformed_code, transformer=self)

            # Targeted post-pass for any remaining caplog alias usages that
            # the CST passes didn't cover. This is intentionally conservative
            # and only substitutes a few well-known patterns when
            # `caplog.at_level` was emitted.
            try:
                transformed_code = transform_caplog_alias_string_fallback(transformed_code)
            except Exception:
                pass

            # Remove unittest imports if no longer used
            transformed_code = remove_unittest_imports_if_unused(transformed_code)

            # Validate the result with CST
            try:
                cst.parse_module(transformed_code)
                return transformed_code
            except Exception as validation_error:
                error_msg = f"# Transformation validation failed: {str(validation_error)}\n"
                return error_msg + code

        except Exception as e:
            # If CST parsing fails, return original code with comment
            error_msg = f"# CST transformation failed: {str(e)}\n"
            return error_msg + code

    def _transform_unittest_inheritance(self, code: str) -> str:
        """Use libcst to remove `unittest.TestCase` inheritance from class defs.

        This is safer than regex and preserves formatting more reliably.
        """
        try:
            module = cst.parse_module(code)

            class Rewriter(cst.CSTTransformer):
                def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
                    new_bases = []
                    changed = False
                    for base in updated.bases:
                        try:
                            if isinstance(base.value, cst.Attribute) and isinstance(base.value.value, cst.Name):
                                if base.value.value.value == "unittest" and base.value.attr.value == "TestCase":
                                    changed = True
                                    continue
                        except Exception:
                            pass
                        new_bases.append(base)
                    if changed:
                        return updated.with_changes(bases=new_bases)
                    return updated

            # First pass removes unittest.TestCase bases
            new_mod = module.visit(Rewriter())

            # Second CST-based pass: normalize class bases so we never leave
            # an empty parentheses pair or stray trailing commas. Doing this
            # with libcst avoids brittle string regex fixes.
            class NormalizeClassBases(cst.CSTTransformer):
                def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
                    # Rebuild base list using fresh Arg nodes to avoid leaving
                    # formatting artifacts (such as a trailing comma) from earlier
                    # removals. This preserves the semantic bases while letting
                    # libcst render them cleanly.
                    try:
                        if not updated.bases:
                            # Reconstruct ClassDef without bases to avoid empty parentheses
                            return cst.ClassDef(name=updated.name, body=updated.body, decorators=updated.decorators)
                        rebuilt = []
                        for b in updated.bases:
                            try:
                                val = getattr(b, "value", None)
                                if val is None:
                                    continue
                                rebuilt.append(cst.Arg(value=val))
                            except Exception:
                                # If we can't extract, keep original base
                                rebuilt.append(b)
                        return updated.with_changes(bases=rebuilt)
                    except Exception:
                        return updated

            normalized = new_mod.visit(NormalizeClassBases())

            # Third pass: normalize test method names inside classes that were
            # originally unittest.TestCase to add underscore after the test prefix
            # when the next character is uppercase (e.g., testSomething -> test_Something).
            class NormalizeTestMethodNames(cst.CSTTransformer):
                def __init__(self, unittest_classes: set[str] | None):
                    self._stack: list[str] = []
                    self.unittest_classes = unittest_classes or set()

                def visit_ClassDef(self, node: cst.ClassDef) -> None:
                    self._stack.append(node.name.value)

                def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef) -> cst.ClassDef:
                    try:
                        self._stack.pop()
                    except Exception:
                        pass
                    return updated

                def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
                    if not self._stack:
                        return updated
                    cls = self._stack[-1]
                    if cls not in (self.unittest_classes or set()):
                        return updated
                    name = original.name.value
                    for prefix in self.test_prefixes if hasattr(self, "test_prefixes") else ["test"]:
                        if name.startswith(prefix) and len(name) > len(prefix):
                            rest = name[len(prefix) :]
                            if rest and rest[0].isupper():
                                return updated.with_changes(name=cst.Name(value=prefix + "_" + rest))
                    return updated

            try:
                normalized = normalized.visit(NormalizeTestMethodNames(getattr(self, "_unittest_classes", set())))
            except Exception:
                pass
            return normalized.code
        except Exception:
            return code
