"""CST-based transformer for unittest to pytest conversion."""

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


class UnittestToPytestTransformer(cst.CSTTransformer):
    """CST-based transformer for unittest to pytest conversion.

    This class systematically transforms unittest code to pytest using libcst:
    1. Parse Python code into AST using libcst
    2. Keep unittest.TestCase class structure but transform inheritance
    3. Transform setUpClass/tearDownClass to class-level fixtures (scope='class')
    4. Transform setUp/tearDown to instance-level fixtures (autouse=True)
    5. Transform assertions using CST node transformations
    6. Generate clean pytest code from transformed CST
    """

    def __init__(self, test_prefixes: list[str] | None = None) -> None:
        self.needs_pytest_import = False
        # Track whether our transforms require `re` and any alias used in the file
        self.needs_re_import = False
        self.re_alias: str | None = None
        # If the module does `from re import search as s` or `from re import search`,
        # capture the local name to prefer `search(...)` form
        self.re_search_name: str | None = None
        self.current_class: str | None = None
        self.setup_code: list[str] = []
        self.teardown_code: list[str] = []
        self.setup_class_code: list[str] = []
        self.teardown_class_code: list[str] = []
        self.setup_module_code: list[str] = []
        self.teardown_module_code: list[str] = []
        self.in_setup = False
        self.in_teardown = False
        self.in_setup_class = False
        self.in_teardown_class = False
        # Test method prefixes used for normalization (e.g., ["test", "spec"])
        self.test_prefixes: list[str] = (test_prefixes or ["test"]) or ["test"]

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

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Inject a module-scoped autouse fixture if setUpModule/tearDownModule were present."""
        if not (self.setup_module_code or self.teardown_module_code):
            return updated_node

        # Build the fixture function: setup_module()
        decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
                args=[
                    cst.Arg(keyword=cst.Name(value="scope"), value=cst.SimpleString(value='"module"')),
                    cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True")),
                ],
            )
        )

        # Determine globals: collect names assigned at top level in setup_module code
        global_names: set[str] = set()
        for line in self.setup_module_code:
            try:
                parsed = cst.parse_statement(line)
                if isinstance(parsed, cst.SimpleStatementLine):
                    for small in parsed.body:
                        if isinstance(small, cst.Assign):
                            for tgt in small.targets:
                                if isinstance(tgt.target, cst.Name):
                                    global_names.add(tgt.target.value)
            except Exception:
                continue

        body_statements: list[cst.BaseStatement] = []
        if global_names:
            body_statements.append(
                cst.SimpleStatementLine(
                    body=[cst.Global(names=[cst.NameItem(name=cst.Name(value=n)) for n in sorted(global_names)])]
                )
            )

        # Add setup module code
        for setup_line in self.setup_module_code:
            try:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
            except Exception:
                try:
                    stmt = cst.parse_module(setup_line).body[0]
                    body_statements.append(stmt)
                except Exception:
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        # Yield
        body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

        # Add teardown module code
        for teardown_line in self.teardown_module_code:
            try:
                body_statements.append(
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))])
                )
            except Exception:
                try:
                    stmt = cst.parse_module(teardown_line).body[0]
                    body_statements.append(stmt)
                except Exception:
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        func = cst.FunctionDef(
            name=cst.Name(value="setup_module"),
            params=cst.Parameters(params=[]),
            body=cst.IndentedBlock(body=body_statements or [cst.SimpleStatementLine(body=[cst.Pass()])]),
            decorators=[decorator],
        )

        # Remove original setUpModule/tearDownModule definitions from body
        filtered_body: list[cst.CSTNode] = []
        for item in updated_node.body:
            if isinstance(item, cst.FunctionDef) and item.name.value in {"setUpModule", "tearDownModule"}:
                continue
            filtered_body.append(item)

        # Prepend our fixture
        new_body = [func] + filtered_body

        # Reset storage
        self.setup_module_code.clear()
        self.teardown_module_code.clear()
        self.needs_pytest_import = True

        return updated_node.with_changes(body=new_body)

    def visit_Decorator(self, node: cst.Decorator) -> bool | None:
        """Transform @unittest.skip / @unittest.skipIf decorators to pytest marks in-place via string fallback.

        This visitor will set the flag to indicate pytest is needed when such decorators are seen.
        """
        # Attempt to recognize patterns like @unittest.skip or @unittest.skipIf
        try:
            dec_code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=node.decorator)])]).code.strip()
            if dec_code.startswith("@unittest.skip") or dec_code.startswith("@unittest.skipIf"):
                self.needs_pytest_import = True
        except Exception:
            pass
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Leave class definition after transformation, adding fixtures."""
        if not self.current_class:
            return updated_node

        # Remove unittest.TestCase from base classes
        new_bases = []
        for base in updated_node.bases:
            if isinstance(base.value, cst.Attribute):
                if (
                    isinstance(base.value.value, cst.Name)
                    and base.value.value.value == "unittest"
                    and base.value.attr.value == "TestCase"
                ):
                    continue  # Skip unittest.TestCase
            new_bases.append(base)
        # Apply bases change first
        updated_node = updated_node.with_changes(bases=new_bases)
        # If no bases and no keywords remain, drop empty parentheses
        if len(new_bases) == 0 and len(updated_node.keywords) == 0:
            updated_node = updated_node.with_changes(lpar=(), rpar=())

        # Generate fixtures if we have setup/teardown code
        new_body = list(updated_node.body.body)  # Convert to list to modify

        # Module-level fixture generation is handled at module leave, not here

        # Add class-level fixture for setUpClass/tearDownClass
        if self.setup_class_code or self.teardown_class_code:
            class_fixture = create_class_fixture(self.setup_class_code, self.teardown_class_code)
            new_body.insert(0, class_fixture)

        # Add instance-level fixtures for setUp/tearDown
        # Create a single instance fixture that handles both setup and teardown
        if self.setup_code or self.teardown_code:
            instance_fixture = create_instance_fixture(self.setup_code, self.teardown_code)
            new_body.insert(0, instance_fixture)

        # Remove original setUp/tearDown methods as they've been converted to fixtures
        filtered_body = []
        for item in new_body:
            if isinstance(item, cst.FunctionDef):
                # Skip setUp, tearDown, setUpClass, tearDownClass methods
                if item.name.value in ["setUp", "tearDown", "setUpClass", "tearDownClass"]:
                    continue
            filtered_body.append(item)
        new_body = filtered_body

        # Reset tracking variables
        self.current_class = None
        self.setup_code.clear()
        self.teardown_code.clear()
        self.setup_class_code.clear()
        self.teardown_class_code.clear()

        # Replace decorators that are unittest.skip / unittest.skipIf with pytest marks
        def _convert_decorators(decorators: list[cst.Decorator]) -> list[cst.Decorator]:
            new_decs: list[cst.Decorator] = []
            for d in decorators:
                # Prefer AST-based detection of unittest.skip and unittest.skipIf
                if isinstance(d.decorator, cst.Call) and isinstance(d.decorator.func, cst.Attribute):
                    func = d.decorator.func
                    if isinstance(func.value, cst.Name) and func.value.value == "unittest":
                        if func.attr.value == "skip" and isinstance(d.decorator, cst.Call):
                            args = d.decorator.args
                            mark = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(func=cst.Attribute(value=mark, attr=cst.Name(value="skip")), args=args)
                            new_decs.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            continue
                        if func.attr.value == "skipIf" and isinstance(d.decorator, cst.Call):
                            args = d.decorator.args
                            mark = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(
                                func=cst.Attribute(value=mark, attr=cst.Name(value="skipif")), args=args
                            )
                            new_decs.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            continue

                # Default: keep original decorator
                new_decs.append(d)
            return new_decs

        new_decorators = _convert_decorators(list(updated_node.decorators))
        updated_node = updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body), decorators=new_decorators
        )

        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Rewrite function decorators for skip/skipIf similarly to classes."""

        def _convert_decorators(decorators: list[cst.Decorator]) -> list[cst.Decorator]:
            new_decs: list[cst.Decorator] = []
            for d in decorators:
                # AST-aware decorator detection for unittest.skip / unittest.skipIf
                if isinstance(d.decorator, cst.Call) and isinstance(d.decorator.func, cst.Attribute):
                    func = d.decorator.func
                    if isinstance(func.value, cst.Name) and func.value.value == "unittest":
                        if func.attr.value == "skip" and isinstance(d.decorator, cst.Call):
                            mark = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(
                                func=cst.Attribute(value=mark, attr=cst.Name(value="skip")), args=d.decorator.args
                            )
                            new_decs.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            continue
                        if func.attr.value == "skipIf" and isinstance(d.decorator, cst.Call):
                            mark = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                            new_call = cst.Call(
                                func=cst.Attribute(value=mark, attr=cst.Name(value="skipif")), args=d.decorator.args
                            )
                            new_decs.append(cst.Decorator(decorator=new_call))
                            self.needs_pytest_import = True
                            continue

                new_decs.append(d)
            return new_decs

        if updated_node.decorators:
            new_decorators = _convert_decorators(list(updated_node.decorators))
            return updated_node.with_changes(decorators=new_decorators)
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit function definitions to track setUp/tearDown methods."""
        if node.name.value == "setUp":
            # Extract setup code from method body
            self._extract_method_body(node, self.setup_code)
        elif node.name.value == "tearDown":
            # Extract teardown code from method body
            self._extract_method_body(node, self.teardown_code)
        elif node.name.value == "setUpClass":
            # Extract setup_class code from method body
            self._extract_method_body(node, self.setup_class_code)
        elif node.name.value == "tearDownClass":
            # Extract teardown_class code from method body
            self._extract_method_body(node, self.teardown_class_code)
        elif node.name.value == "setUpModule":
            self._extract_method_body(node, self.setup_module_code)
        elif node.name.value == "tearDownModule":
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

            # Apply CST transformer (handles TestCase removal and fixture injection)
            transformed_cst = module.visit(self)
            transformed_code = transformed_cst.code

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
