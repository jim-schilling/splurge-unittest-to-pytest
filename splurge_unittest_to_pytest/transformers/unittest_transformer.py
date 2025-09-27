"""Lightweight UnittestToPytestTransformer shim.

This minimal implementation provides the public API used by tests
(`UnittestToPytestTransformer.transform_code`) while delegating
heavy-duty assertion string transforms to the extracted
`assert_transformer.transform_assertions_string_based` helpers.

The full CST-based transformer was large and has been refactored into
smaller modules; this shim keeps compatibility for the test-suite.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import libcst as cst

from ..helpers.utility import (
    safe_replace_one_arg_call,
    safe_replace_two_arg_call,
    split_two_args_balanced,
)
from .assert_transformer import (
    transform_assert_count_equal,
    transform_assert_dict_equal,
    transform_assert_equal,
    transform_assert_false,
    transform_assert_in,
    transform_assert_is,
    transform_assert_is_not,
    transform_assert_isinstance,
    transform_assert_list_equal,
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
    transform_assertions_string_based,
    transform_fail,
    transform_skip_test,
)
from .fixture_transformer import (
    create_class_fixture,
    create_instance_fixture,
)
from .subtest_transformer import (
    body_uses_subtests,
    convert_simple_subtests_to_parametrize,
    convert_subtests_in_body,
    ensure_subtests_param,
)

# mypy: ignore-errors


class UnittestToPytestTransformer:
    """Minimal transformer exposing transform_code used by tests.

    This intentionally implements a conservative, string-based
    transformation pipeline that is good enough for the unit tests in
    this repository. It does not attempt to be a full CST transformer
    (that logic lives in other modules).
    """

    def __init__(self, test_prefixes: list[str] | None = None, parametrize: bool = False) -> None:
        self.test_prefixes = test_prefixes or ["test"]
        self.parametrize = parametrize

    def _add_pytest_import(self, code: str) -> str:
        if "import pytest" in code or "from pytest" in code:
            return code

        # Find insertion point: first non-empty, non-shebang, non-comment line
        lines = code.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if not s or s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
                continue
            insert_at = i
            break

        lines.insert(insert_at, "import pytest")
        lines.insert(insert_at + 1, "")
        return "\n".join(lines)

    def transform_code(self, code: str) -> str:
        """Transform unittest-style code into pytest-style code (best-effort).

        The implementation is intentionally small: it removes
        `unittest.TestCase` inheritance, delegates assertion rewrites to
        the string-based helpers and ensures `import pytest` is present
        when appropriate.
        """
        try:
            # Parse to ensure valid Python; if parsing fails, return original
            cst.parse_module(code)
        except Exception:
            # If parsing fails, return original code (tests expect a string)
            return code

        # Remove unittest.TestCase inheritance in class definitions
        code = re.sub(r"class\s+(\w+)\s*\(\s*unittest\.TestCase\s*\)", r"class \1:", code)

        # Apply assertion-level string transforms (fallback implementation)
        code = transform_assertions_string_based(code, test_prefixes=self.test_prefixes)

        # Replace explicit unittest.main() with pytest.main()
        code = re.sub(r"unittest\.main\s*\(\s*\)", "pytest.main()", code)

        # If we've removed TestCase or inserted pytest-specific code, ensure pytest import
        if "import pytest" not in code:
            # Heuristic: add pytest import when the original code referenced unittest.TestCase
            # or if transformed code now contains pytest-specific markers
            if (
                "unittest.TestCase" in code
                or "pytest." in code
                or "with self.assertRaises" in code
                or "assert " in code
            ):
                code = self._add_pytest_import(code)

        return code


"""CST-based transformer for unittest to pytest conversion."""


class UnittestToPytestCSTTransformer(cst.CSTTransformer):
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

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit class definition to check for unittest.TestCase inheritance."""
        self.current_class = node.name.value

        # Check for unittest.TestCase inheritance
        for base in node.bases:
            if isinstance(base.value, cst.Attribute):
                if (
                    isinstance(base.value.value, cst.Name)
                    and base.value.value.value == "unittest"
                    and base.value.attr.value == "TestCase"
                ):
                    self.needs_pytest_import = True
                    # Mark this class for transformation
                    break
        return None  # Continue traversal

    def _rewrite_skip_decorators(self, decorators: list[cst.Decorator] | None) -> list[cst.Decorator] | None:
        """Rewrite decorators like `@unittest.skip` and `@unittest.skipIf` to
        `@pytest.mark.skip` and `@pytest.mark.skipif` respectively.

        Returns updated decorator list or None.
        """
        if not decorators:
            return decorators

        new_decorators: list[cst.Decorator] = []
        changed = False
        for d in decorators:
            try:
                dec = d.decorator
                # We expect a Call: unittest.skip(...)
                if isinstance(dec, cst.Call) and isinstance(dec.func, cst.Attribute):
                    owner = dec.func.value
                    name = dec.func.attr
                    if isinstance(owner, cst.Name) and owner.value == "unittest" and isinstance(name, cst.Name):
                        if name.value == "skip":
                            # Build @pytest.mark.skip(<args...>)
                            mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(
                                func=cst.Attribute(value=mark_attr, attr=cst.Name(value="skip")), args=dec.args
                            )
                            new_decorators.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            changed = True
                            continue
                        elif name.value == "skipIf":
                            mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(
                                func=cst.Attribute(value=mark_attr, attr=cst.Name(value="skipif")), args=dec.args
                            )
                            new_decorators.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            changed = True
                            continue
                # Otherwise keep as-is
                new_decorators.append(d)
            except Exception:
                new_decorators.append(d)

        return new_decorators if changed else decorators

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Inject a module-scoped autouse fixture if setUpModule/tearDownModule were present."""
        new_body = list(updated_node.body)

        # Determine insertion index after imports and module docstring
        insert_index = 0
        for i, node in enumerate(new_body):
            # Keep moving past imports and module-level docstring
            if isinstance(node, cst.Import | cst.ImportFrom):
                insert_index = i + 1
                continue
            if (
                isinstance(node, cst.SimpleStatementLine)
                and len(node.body) == 1
                and isinstance(node.body[0], cst.Expr)
                and isinstance(node.body[0].value, cst.SimpleString)
            ):
                insert_index = i + 1
                continue
            break

        cleaned_body: list[cst.CSTNode] = []
        remove_names = {"setUp", "tearDown", "setUpClass", "tearDownClass"}

        # Iterate through top-level nodes; for ClassDefs, insert per-class fixtures and remove original methods
        for node in new_body:
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
                            setup_cls = self._per_class_setup_class.get(cls_name, [])
                            teardown_cls = self._per_class_teardown_class.get(cls_name, [])
                            if setup_cls or teardown_cls:
                                class_fixture = create_class_fixture(setup_cls, teardown_cls)
                                class_body_items.append(class_fixture)
                                self.needs_pytest_import = True
                        if cls_name in self._per_class_setup or cls_name in self._per_class_teardown:
                            setup_inst = self._per_class_setup.get(cls_name, [])
                            teardown_inst = self._per_class_teardown.get(cls_name, [])
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
            if self.setup_class_code or self.teardown_class_code:
                class_fixture = create_class_fixture(self.setup_class_code, self.teardown_class_code)
                module_fixtures.append(class_fixture)
                self.needs_pytest_import = True
            if self.setup_code or self.teardown_code:
                inst_fixture = create_instance_fixture(self.setup_code, self.teardown_code)
                module_fixtures.append(inst_fixture)
                self.needs_pytest_import = True
        except Exception:
            pass

        # Clear module-level collected code to avoid duplication
        self.setup_class_code = []
        self.teardown_class_code = []
        self.setup_code = []
        self.teardown_code = []

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

        return updated_node.with_changes(body=final_body)

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Handle function-level rewrites: parametrize conversion, subTest -> subtests, and assertLogs wrapping."""
        try:
            # Rewrite function-level decorators (skip/skipIf)
            updated_node = updated_node.with_changes(
                decorators=self._rewrite_skip_decorators(list(updated_node.decorators or []))
            )

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

            # Then wrap assertLogs/assertNoLogs patterns
            new_body = self._wrap_assert_logs_in_block(body_with_subtests)
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        except Exception:
            return updated_node

    def _convert_simple_subtests_to_parametrize(
        self, original_func: cst.FunctionDef, updated_func: cst.FunctionDef
    ) -> cst.FunctionDef | None:
        """Conservatively convert patterns like:

        for val in iterable:
            with self.subTest(val):
                assert check(val)

        into a pytest.mark.parametrize decorator on the function when:
        - the For body is a single With
        - the With calls self.subTest with a single positional arg which is a Name
        - the With body contains a single SimpleStatementLine with an assert

        Return a new FunctionDef with the added decorator and the For replaced by a simple body
        using the new parameter name. If not applicable, return None.
        """
        try:
            body_stmts = list(updated_func.body.body)
            if len(body_stmts) == 0:
                return None

            # Look for a leading For statement that matches our pattern
            first = body_stmts[0]
            if not isinstance(first, cst.For):
                return None

            # Ensure For body is a single With
            for_body = first.body
            if not isinstance(for_body, cst.IndentedBlock) or len(for_body.body) != 1:
                return None
            inner = for_body.body[0]
            if not isinstance(inner, cst.With):
                return None

            # Ensure the With has a single call to self.subTest with a single arg
            if len(inner.items) != 1:
                return None
            call = inner.items[0].item
            if not isinstance(call, cst.Call) or not isinstance(call.func, cst.Attribute):
                return None
            if not isinstance(call.func.value, cst.Name) or call.func.value.value not in {"self", "cls"}:
                return None
            if call.func.attr.value != "subTest":
                return None
            # Require exactly one arg (positional or keyword)
            if len(call.args) != 1:
                return None

            single_arg = call.args[0]
            # Support positional: subTest(i)
            if single_arg.keyword is None:
                arg_expr = single_arg.value
                # Only support simple Name for positional form for safety
                if not isinstance(arg_expr, cst.Name):
                    return None
                param_name = arg_expr.value
                # We will require loop target to match this name later
            else:
                # Keyword form: subTest(i=i) -> keyword name is the param name, value must be Name
                if not isinstance(single_arg.keyword, cst.Name):
                    return None
                kw_name = single_arg.keyword.value
                arg_expr = single_arg.value
                if not isinstance(arg_expr, cst.Name):
                    return None
                # For safety, require the keyword value to reference the loop variable (same name)
                # e.g., for i in [..]: with self.subTest(i=i):
                if arg_expr.value != first.target.value if isinstance(first.target, cst.Name) else True:
                    return None
                param_name = kw_name

            # Ensure the With body contains at least one statement; allow multiple
            inner_body = inner.body
            if not isinstance(inner_body, cst.IndentedBlock) or len(inner_body.body) < 1:
                return None
            # We allow multiple statements but ensure they are simple statements (not nested defs)
                for stmt in inner_body.body:
                    if not isinstance(stmt, cst.SimpleStatementLine | cst.If | cst.Expr | cst.Assign):
                        # Be conservative; if body contains complex nodes, skip parametrize
                        return None

            # At this point param_name is set from either form

            # Extract param values from the For.iter if it's a literal list/tuple
            iter_node = first.iter
            values: list[cst.BaseExpression] = []

            def _extract_from_list_or_tuple(node: cst.BaseExpression) -> list[cst.BaseExpression] | None:
                vals: list[cst.BaseExpression] = []
                if isinstance(node, cst.List | cst.Tuple):
                    for el in node.elements:
                        if isinstance(el, cst.Element):
                            vals.append(el.value)
                    return vals
                return None

            # 1) Direct literal list/tuple: for x in [..] or (..)
            maybe_vals = _extract_from_list_or_tuple(iter_node)
            if maybe_vals is not None:
                values = maybe_vals
            else:
                # 2) range(start, stop, step?) with literal numeric args
                if (
                    isinstance(iter_node, cst.Call)
                    and isinstance(iter_node.func, cst.Name)
                    and iter_node.func.value == "range"
                ):
                    # Accept only literal integer args for range
                    ok = True
                    args_vals: list[int] = []
                    for a in iter_node.args:
                        if isinstance(a.value, cst.Integer):
                            try:
                                args_vals.append(int(a.value.value))
                            except Exception:
                                ok = False
                                break
                        else:
                            ok = False
                            break
                    if ok and len(args_vals) in {1, 2, 3}:
                        # Expand range to explicit values conservatively (small ranges only)
                        # Reject very large ranges to avoid huge param lists
                        try:
                            if len(args_vals) == 1:
                                start, stop, step = 0, args_vals[0], 1
                            elif len(args_vals) == 2:
                                start, stop = args_vals[0], args_vals[1]
                                step = 1
                            else:
                                start, stop, step = args_vals[0], args_vals[1], args_vals[2]
                            # Only allow small ranges up to 20 elements
                            rng = list(range(start, stop, step))
                            if len(rng) > 20:
                                return None
                            for v in rng:
                                values.append(cst.Integer(value=str(v)))
                        except Exception:
                            return None
                    else:
                        return None
                else:
                    # 3) Name reference: check for an earlier assignment in the same function
                    if isinstance(iter_node, cst.Name):
                        name_to_find = iter_node.value
                        # Walk function body statements before the For to find an assignment like: name = [..]
                        assignments_found = None
                        for prev in body_stmts:
                            if prev is first:
                                break
                            # Only consider simple assignment statements
                            if isinstance(prev, cst.SimpleStatementLine) and len(prev.body) == 1:
                                expr = prev.body[0]
                                if isinstance(expr, cst.Assign):
                                    # single target Name
                                    if len(expr.targets) == 1 and isinstance(expr.targets[0].target, cst.Name):
                                        tgt = expr.targets[0].target.value
                                        if tgt == name_to_find:
                                            maybe_vals = _extract_from_list_or_tuple(expr.value)
                                            if maybe_vals is not None:
                                                assignments_found = maybe_vals
                                                # continue scanning to ensure no reassignment occurs before For
                                                continue
                                            else:
                                                assignments_found = None
                        if assignments_found:
                            values = assignments_found
                        else:
                            return None
                    else:
                        return None

            # Build a pytest.mark.parametrize decorator using extracted values
            param_list = cst.List([cst.Element(value=v) for v in values])
            params_str = cst.SimpleString(value=f'"{param_name}"')
            # Build decorator: @pytest.mark.parametrize("<param>", [<values>])
            mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
            param_call = cst.Call(
                func=cst.Attribute(value=mark_attr, attr=cst.Name(value="parametrize")),
                args=[
                    cst.Arg(value=params_str),
                    cst.Arg(value=param_list),
                ],
            )
            new_decorator = cst.Decorator(decorator=param_call)

            # If the function already has a parametrize decorator, be idempotent and skip
            existing_decorators = list(updated_func.decorators or [])
            for d in existing_decorators:
                try:
                    if isinstance(d.decorator, cst.Call):
                        f = d.decorator.func
                        # detect patterns like pytest.mark.parametrize
                        if (
                            isinstance(f, cst.Attribute)
                            and isinstance(f.attr, cst.Name)
                            and f.attr.value == "parametrize"
                        ):
                            return None
                        # or direct name 'parametrize' (unlikely) — be conservative
                        if isinstance(f, cst.Name) and f.value == "parametrize":
                            return None
                except Exception:
                    continue

            new_decorators = [new_decorator] + existing_decorators

            # Ensure the loop target matches the subTest arg name for safe replacement
            if not isinstance(first.target, cst.Name) or first.target.value != param_name:
                return None

            # Use the inner body statements as the new function body (preserving multiple statements)
            new_body = cst.IndentedBlock(body=list(inner_body.body))

            new_func = updated_func.with_changes(decorators=new_decorators, body=new_body)
            # Mark that pytest import will be needed
            self.needs_pytest_import = True
            return new_func
        except Exception:
            return None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit function definitions to track setUp/tearDown methods."""
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
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Convert the statement line to code using the module's code generation
                    stmt_module = cst.Module(body=[stmt])
                    target_list.append(stmt_module.code.strip())

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

    def _wrap_assert_logs_in_block(self, statements: list[cst.BaseStatement]) -> list[cst.BaseStatement]:
        """Scan a list of statements and wrap `self.assertLogs`/`self.assertNoLogs`
        calls followed by a statement into a With block that contains the following
        statement as its body.

        This mirrors the string-based fallback which only indents the immediate
        next non-empty line under the context manager.
        """
        out: list[cst.BaseStatement] = []
        i = 0
        while i < len(statements):
            stmt = statements[i]
            # Only consider simple statement lines with a single Expr containing a Call
            wrapped = False
            if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                expr = stmt.body[0].value
                if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Attribute):
                    func = expr.func
                    if isinstance(func.value, cst.Name) and func.value.value in {"self", "cls"}:
                        if func.attr.value in {"assertLogs", "assertNoLogs"}:
                            # There is a following statement to wrap
                            if i + 1 < len(statements):
                                next_stmt = statements[i + 1]
                                # Create With node using the same call as the context expression
                                with_item = cst.WithItem(cst.Call(func=expr.func, args=expr.args))
                                # Build the block body using the next statement as the single body element
                                body_block = cst.IndentedBlock(body=[next_stmt])
                                with_node = cst.With(body=body_block, items=[with_item])
                                out.append(with_node)
                                i += 2
                                wrapped = True
            if not wrapped:
                out.append(stmt)
                i += 1
        return out

    def _convert_subtests_in_body(self, statements: list[cst.BaseStatement]) -> list[cst.BaseStatement]:
        # Delegate to implementation in subtest module
        return convert_subtests_in_body(statements)

    def _body_uses_subtests(self, statements: list[cst.BaseStatement]) -> bool:
        # Delegate detection to subtest module
        return body_uses_subtests(statements)

    def _ensure_subtests_param(self, func: cst.FunctionDef) -> cst.FunctionDef:
        # Delegate parameter injection to subtest module
        return ensure_subtests_param(func)

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
                    "skipTest": transform_skip_test,
                    "fail": transform_fail,
                    # raises / regex handled with lambdas so we can pass transformer context when needed
                    "assertRaises": transform_assert_raises,
                    "assertRaisesRegex": transform_assert_raises_regex,
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
                        # new_node may be a cst.Assert (an expression node) or other CST node;
                        # annotate return as BaseExpression to satisfy libcst typed transformer signature
                        return new_node  # type: ignore[return-value]
                    except Exception:
                        # On any transformation error, fall back to the original node
                        return updated_node

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

    # create_class_fixture moved to transformers.fixture_transformer.create_class_fixture

    # create_instance_fixture moved to transformers.fixture_transformer.create_instance_fixture

    # create_teardown_fixture moved to transformers.fixture_transformer.create_teardown_fixture

    # Thin wrapper methods for assertion transforms removed; mapping uses functions from assert_transformer

    def _replace_call_node(self, old_node: cst.Call, new_node: cst.Call) -> None:
        """Helper method to replace a call node in the CST.

        This is a simplified approach - in a full implementation,
        this would properly integrate with libcst's node replacement mechanisms.
        Since we're currently using string-based transformations, this method
        is not actively used but is provided for future CST-based implementations.
        """
        # In a full CST-based implementation, this would:
        # 1. Store the mapping of old_node -> new_node
        # 2. Use libcst's node replacement mechanisms
        # 3. Handle the replacement during the leave phase

        # For now, this is a no-op since we use string-based transformations
        # But we keep the method signature for future implementation
        pass

    def transform_code(self, code: str) -> str:
        """Transform unittest code to pytest code using CST first, then fallback string ops."""
        try:
            # Parse the code into CST to understand the structure
            module = cst.parse_module(code)

            # Apply CST transformer (handles fixture injection)
            transformed_cst = module.visit(self)
            transformed_code = transformed_cst.code

            # Also perform simple string-based removal of 'unittest.TestCase' inheritance
            # for cases not handled via CST rewriting.
            transformed_code = self._transform_unittest_inheritance(transformed_code)

            # Transform assertion methods using string replacement fallback
            transformed_code = transform_assertions_string_based(transformed_code, test_prefixes=self.test_prefixes)

            # Add necessary imports
            transformed_code = self._add_pytest_imports(transformed_code)

            # Remove unittest imports if no longer used
            transformed_code = self._remove_unittest_imports_if_unused(transformed_code)

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
        """Remove unittest.TestCase inheritance from class definitions."""
        # Simple string replacement for inheritance
        import re

        code = re.sub(r"class\s+(\w+)\s*\(\s*unittest\.TestCase\s*\)", r"class \1", code)
        return code

    def _split_two_args_balanced(self, s: str) -> tuple[str, str] | None:
        return split_two_args_balanced(s)

    def _safe_replace_two_arg_call(self, code: str, func_name: str, format_fn: Callable[[str, str], str]) -> str:
        return safe_replace_two_arg_call(code, func_name, format_fn)

    def _safe_replace_one_arg_call(self, code: str, func_name: str, format_fn: Callable[[str], str]) -> str:
        return safe_replace_one_arg_call(code, func_name, format_fn)

    # String-based assertion fallback moved to transform_assertions_string_based in assert_transformer

    # Fixture string-based fallback moved to transformers.fixture_transformer.transform_fixtures_string_based

    def _add_pytest_imports(self, code: str) -> str:
        """Add necessary pytest imports if not already present."""

        # Check if pytest is already imported
        if "import pytest" not in code and "from pytest" not in code:
            # Add pytest import at the top
            lines = code.split("\n")
            insert_index = 0

            # Find the first non-empty line
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith("#"):
                    insert_index = i
                    break

            lines.insert(insert_index, "import pytest")
            lines.insert(insert_index + 1, "")
            code = "\n".join(lines)

        # If any transforms produced regex uses, ensure `re` is imported (respect alias if present)
        if getattr(self, "needs_re_import", False):
            # If caller did `from re import search`, there's no need to add an import
            if getattr(self, "re_search_name", None):
                pass
            else:
                # If an alias was detected in original imports, use it; otherwise add `import re`
                re_name = getattr(self, "re_alias", None) or "re"
                # If the chosen name isn't present as an import, add it
                if f"import {re_name}" not in code and f"from {re_name} import" not in code:
                    lines = code.split("\n")
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.strip().startswith("#"):
                            insert_index = i
                            break
                    # If alias is not the default 're' (i.e., re_name != 're'), we still add 'import re as <alias>'
                    if re_name == "re":
                        lines.insert(insert_index, "import re")
                    else:
                        lines.insert(insert_index, f"import re as {re_name}")
                    lines.insert(insert_index + 1, "")
                    code = "\n".join(lines)

        return code

    def _remove_unittest_imports_if_unused(self, code: str) -> str:
        """Remove `import unittest` lines if `unittest` is no longer referenced."""
        lines = code.split("\n")
        candidate_indices: list[int] = []
        non_candidate_lines: list[str] = []

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import unittest") or stripped.startswith("from unittest import"):
                candidate_indices.append(idx)
            else:
                non_candidate_lines.append(line)

        # If no candidates, return as-is
        if not candidate_indices:
            return code

        rest = "\n".join(non_candidate_lines)
        # If 'unittest' is not referenced elsewhere, drop the import lines
        if "unittest" not in rest:
            kept_lines = [line for i, line in enumerate(lines) if i not in candidate_indices]
            return "\n".join(kept_lines)

        return code


# Public API compatibility: historically the package exported
# `UnittestToPytestTransformer` as the main transformer class. During
# refactors we introduced `UnittestToPytestCSTTransformer` (the full
# libcst-based implementation) and kept a lightweight shim under the
# original name. Many tests and callers expect a CST-style transformer
# (with methods like `on_visit` and attributes such as
# `needs_pytest_import`), so expose the CST implementation under the
# historical public name to preserve runtime behavior.
# Preserve the original lightweight shim under a historical alias in case
# external code depended on the old name. Prefer explicit use of the
# CST implementation by importing `UnittestToPytestCSTTransformer`.
HistoricalUnittestToPytestTransformer = UnittestToPytestTransformer  # type: ignore
