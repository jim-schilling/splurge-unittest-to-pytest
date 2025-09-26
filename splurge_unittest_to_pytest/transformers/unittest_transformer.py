"""CST-based transformer for unittest to pytest conversion."""

from collections.abc import Callable

import libcst as cst


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
                    body=[
                        cst.Global(
                            names=[cst.NameItem(name=cst.Name(value=n)) for n in sorted(global_names)]
                        )
                    ]
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
            class_fixture = self._create_class_fixture()
            new_body.insert(0, class_fixture)

        # Add instance-level fixtures for setUp/tearDown
        # Create a single instance fixture that handles both setup and teardown
        if self.setup_code or self.teardown_code:
            instance_fixture = self._create_instance_fixture()
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

        return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

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

    def visit_Call(self, node: cst.Call) -> bool | None:
        """Visit function calls to detect pytest.raises usage."""
        # Handle pytest.raises calls by setting the needs_pytest_import flag
        if isinstance(node.func, cst.Attribute):
            if isinstance(node.func.value, cst.Name) and node.func.value.value == "pytest":
                if node.func.attr.value == "raises":
                    self.needs_pytest_import = True
        return True  # Continue traversal

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

    def _create_class_fixture(self) -> cst.FunctionDef:
        """Create a class-level fixture for setUpClass/tearDownClass."""
        decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
                args=[
                    cst.Arg(keyword=cst.Name(value="scope"), value=cst.SimpleString(value='"class"')),
                    cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True")),
                ],
            )
        )

        # Create fixture body with extracted setup and teardown code
        body_statements = []

        # Add setup_class code if available
        for setup_line in self.setup_class_code:
            try:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
            except Exception:
                # If parsing as expression fails, parse as statement
                try:
                    parsed_stmt = cst.parse_module(setup_line).body[0]
                    if isinstance(parsed_stmt, cst.SimpleStatementLine):
                        body_statements.append(parsed_stmt)
                except Exception:
                    # If all else fails, create a comment
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        # Add yield point
        body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

        # Add teardown_class code if available
        for teardown_line in self.teardown_class_code:
            try:
                body_statements.append(
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))])
                )
            except Exception:
                # If parsing as expression fails, parse as statement
                try:
                    parsed_stmt = cst.parse_module(teardown_line).body[0]
                    if isinstance(parsed_stmt, cst.SimpleStatementLine):
                        body_statements.append(parsed_stmt)
                except Exception:
                    # If all else fails, create a comment
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        # Fallback to pass if no code was extracted
        if not body_statements:
            body_statements = [
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]),
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
            ]

        # Create fixture function
        func_name = cst.FunctionDef(
            name=cst.Name(value="setup_class"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name(value="cls"), annotation=None)]),
            body=cst.IndentedBlock(body=body_statements),
            decorators=[decorator],
            returns=None,
        )

        return func_name

    def _create_instance_fixture(self) -> cst.FunctionDef:
        """Create an instance-level fixture for setUp/tearDown."""
        # Create fixture decorator with autouse=True
        decorator = cst.Decorator(
            decorator=cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture")),
                args=[cst.Arg(keyword=cst.Name(value="autouse"), value=cst.Name(value="True"))],
            )
        )

        # Create fixture body with extracted setup and teardown code
        body_statements = []

        # Add setup code if available
        for setup_line in self.setup_code:
            try:
                body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(setup_line))]))
            except Exception:
                # If parsing as expression fails, parse as statement
                try:
                    parsed_stmt = cst.parse_module(setup_line).body[0]
                    if isinstance(parsed_stmt, cst.SimpleStatementLine):
                        body_statements.append(parsed_stmt)
                except Exception:
                    # If all else fails, create a comment
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        # Add yield point
        body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

        # Add teardown code if available
        for teardown_line in self.teardown_code:
            try:
                body_statements.append(
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))])
                )
            except Exception:
                # If parsing as expression fails, parse as statement
                try:
                    parsed_stmt = cst.parse_module(teardown_line).body[0]
                    if isinstance(parsed_stmt, cst.SimpleStatementLine):
                        body_statements.append(parsed_stmt)
                except Exception:
                    # If all else fails, create a comment
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        # Fallback to pass if no code was extracted
        if not body_statements:
            body_statements = [
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]),
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]),
            ]

        # Create fixture function
        func_name = cst.FunctionDef(
            name=cst.Name(value="setup_method"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name(value="self"), annotation=None)]),
            body=cst.IndentedBlock(body=body_statements),
            decorators=[decorator],
            returns=None,
        )

        return func_name

    def _create_teardown_fixture(self) -> cst.FunctionDef:
        """Create an instance-level teardown fixture for tearDown using yield-first pattern."""
        decorator = cst.Decorator(
            decorator=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="fixture"))
        )

        body_statements = []
        # Yield first to model teardown after test
        body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=None))]))

        for teardown_line in self.teardown_code:
            try:
                body_statements.append(
                    cst.SimpleStatementLine(body=[cst.Expr(value=cst.parse_expression(teardown_line))])
                )
            except Exception:
                try:
                    parsed_stmt = cst.parse_module(teardown_line).body[0]
                    if isinstance(parsed_stmt, cst.SimpleStatementLine):
                        body_statements.append(parsed_stmt)
                except Exception:
                    body_statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))]))

        func_name = cst.FunctionDef(
            name=cst.Name(value="teardown_method"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name(value="self"), annotation=None)]),
            body=cst.IndentedBlock(body=body_statements),
            decorators=[decorator],
            returns=None,
        )
        return func_name

    def _transform_assert_equal(self, node: cst.Call) -> cst.Call:
        """Transform assertEqual to assert ==."""
        if len(node.args) >= 2:
            # Convert: self.assertEqual(a, b) -> assert a == b
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_true(self, node: cst.Call) -> cst.Call:
        """Transform assertTrue to assert."""
        if len(node.args) >= 1:
            # Convert: self.assertTrue(condition) -> assert condition
            new_func = cst.Name(value="assert")
            return cst.Call(func=new_func, args=[node.args[0]])
        return node

    def _transform_assert_false(self, node: cst.Call) -> cst.Call:
        """Transform assertFalse to assert not."""
        if len(node.args) >= 1:
            # Convert: self.assertFalse(condition) -> assert not condition
            new_func = cst.Name(value="assert")
            new_args = [cst.Arg(value=cst.UnaryOperation(operator=cst.Not(), expression=node.args[0].value))]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_is(self, node: cst.Call) -> cst.Call:
        """Transform assertIs to assert is."""
        if len(node.args) >= 2:
            # Convert: self.assertIs(a, b) -> assert a is b
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_in(self, node: cst.Call) -> cst.Call:
        """Transform assertIn to assert in."""
        if len(node.args) >= 2:
            # Convert: self.assertIn(item, container) -> assert item in container
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_raises(self, node: cst.Call) -> cst.Call:
        """Transform assertRaises to pytest.raises context manager."""
        if len(node.args) >= 2:
            # Convert: self.assertRaises(Exception, func) -> with pytest.raises(Exception):
            exception_type = node.args[0].value
            code_to_test = node.args[1].value

            # For now, return a comment indicating the transformation needed
            # In a full implementation, this would create a with statement
            new_func = cst.Name(value="pytest")
            new_attr = cst.Attribute(value=new_func, attr=cst.Name(value="raises"))
            new_args = [
                cst.Arg(value=exception_type),
                cst.Arg(value=cst.Call(func=new_func, args=[cst.Arg(value=code_to_test)])),
            ]
            return cst.Call(func=new_attr, args=new_args)
        return node  # Return original node if transformation doesn't apply

    def _transform_assert_dict_equal(self, node: cst.Call) -> cst.Call:
        """Transform assertDictEqual to assert ==."""
        if len(node.args) >= 2:
            # Convert: self.assertDictEqual(dict1, dict2) -> assert dict1 == dict2
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_list_equal(self, node: cst.Call) -> cst.Call:
        """Transform assertListEqual to assert ==."""
        if len(node.args) >= 2:
            # Convert: self.assertListEqual(list1, list2) -> assert list1 == list2
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_set_equal(self, node: cst.Call) -> cst.Call:
        """Transform assertSetEqual to assert ==."""
        if len(node.args) >= 2:
            # Convert: self.assertSetEqual(set1, set2) -> assert set1 == set2
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_tuple_equal(self, node: cst.Call) -> cst.Call:
        """Transform assertTupleEqual to assert ==."""
        if len(node.args) >= 2:
            # Convert: self.assertTupleEqual(tuple1, tuple2) -> assert tuple1 == tuple2
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Comparison(
                        left=node.args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_raises_regex(self, node: cst.Call) -> cst.Call:
        """Transform assertRaisesRegex to pytest.raises with match."""
        if len(node.args) >= 3:
            # Convert: self.assertRaisesRegex(Exception, pattern, func) -> with pytest.raises(Exception, match=pattern):
            exception_type = node.args[0].value
            code_to_test = node.args[2].value

            new_func = cst.Name(value="pytest")
            new_attr = cst.Attribute(value=new_func, attr=cst.Name(value="raises"))
            new_args = [
                cst.Arg(value=exception_type),
                cst.Arg(value=cst.Call(func=new_func, args=[cst.Arg(value=code_to_test)])),
            ]
            return cst.Call(func=new_attr, args=new_args)
        return node  # Return original node if transformation doesn't apply

    def _transform_assert_isinstance(self, node: cst.Call) -> cst.Call:
        """Transform assertIsInstance to isinstance assert."""
        if len(node.args) >= 2:
            # Convert: self.assertIsInstance(obj, class) -> assert isinstance(obj, class)
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.Call(
                        func=cst.Name(value="isinstance"),
                        args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

    def _transform_assert_not_isinstance(self, node: cst.Call) -> cst.Call:
        """Transform assertNotIsInstance to not isinstance assert."""
        if len(node.args) >= 2:
            # Convert: self.assertNotIsInstance(obj, class) -> assert not isinstance(obj, class)
            new_func = cst.Name(value="assert")
            new_args = [
                cst.Arg(
                    value=cst.UnaryOperation(
                        operator=cst.Not(),
                        expression=cst.Call(
                            func=cst.Name(value="isinstance"),
                            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
                        ),
                    )
                )
            ]
            return cst.Call(func=new_func, args=new_args)
        return node

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
            transformed_code = self._transform_assertions_string_based(transformed_code)

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
        """Split a string containing two arguments into (arg1, arg2) respecting brackets and quotes."""
        depth_paren = depth_brack = depth_brace = 0
        in_single = in_double = False
        escape = False
        for i, ch in enumerate(s):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if in_single:
                if ch == "'":
                    in_single = False
                continue
            if in_double:
                if ch == '"':
                    in_double = False
                continue
            if ch == "'":
                in_single = True
                continue
            if ch == '"':
                in_double = True
                continue
            if ch == "(":
                depth_paren += 1
                continue
            if ch == ")":
                if depth_paren > 0:
                    depth_paren -= 1
                continue
            if ch == "[":
                depth_brack += 1
                continue
            if ch == "]":
                if depth_brack > 0:
                    depth_brack -= 1
                continue
            if ch == "{":
                depth_brace += 1
                continue
            if ch == "}":
                if depth_brace > 0:
                    depth_brace -= 1
                continue
            if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
                left = s[:i].strip()
                right = s[i + 1 :].strip()
                return left, right
        return None

    def _safe_replace_two_arg_call(self, code: str, func_name: str, format_fn: Callable[[str, str], str]) -> str:
        """Safely replace calls like self.func_name(arg1, arg2) using balanced parsing.

        format_fn: function taking (arg1: str, arg2: str) -> str replacement
        """
        needle = f"self.{func_name}("
        i = 0
        out_parts: list[str] = []
        while True:
            j = code.find(needle, i)
            if j == -1:
                out_parts.append(code[i:])
                break
            # append up to call
            out_parts.append(code[i:j])
            k = j + len(needle)
            # find matching closing paren for this call
            depth = 1
            in_single = in_double = False
            escape = False
            while k < len(code):
                ch = code[k]
                if escape:
                    escape = False
                    k += 1
                    continue
                if ch == "\\":
                    escape = True
                    k += 1
                    continue
                if in_single:
                    if ch == "'":
                        in_single = False
                    k += 1
                    continue
                if in_double:
                    if ch == '"':
                        in_double = False
                    k += 1
                    continue
                if ch == "'":
                    in_single = True
                    k += 1
                    continue
                if ch == '"':
                    in_double = True
                    k += 1
                    continue
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if depth != 0:
                # unmatched; give up and copy as-is
                out_parts.append(code[j:k])
                i = k
                continue
            inner = code[j + len(needle) : k]
            split = self._split_two_args_balanced(inner)
            if not split:
                # cannot split; copy original
                out_parts.append(code[j : k + 1])
                i = k + 1
                continue
            a1, a2 = split
            replacement = format_fn(a1, a2)
            out_parts.append(replacement)
            i = k + 1
        return "".join(out_parts)

    def _safe_replace_one_arg_call(self, code: str, func_name: str, format_fn: Callable[[str], str]) -> str:
        """Safely replace calls like self.func_name(arg) respecting nesting/quotes."""
        needle = f"self.{func_name}("
        i = 0
        out_parts: list[str] = []
        while True:
            j = code.find(needle, i)
            if j == -1:
                out_parts.append(code[i:])
                break
            out_parts.append(code[i:j])
            k = j + len(needle)
            depth = 1
            in_single = in_double = False
            escape = False
            while k < len(code):
                ch = code[k]
                if escape:
                    escape = False
                    k += 1
                    continue
                if ch == "\\":
                    escape = True
                    k += 1
                    continue
                if in_single:
                    if ch == "'":
                        in_single = False
                    k += 1
                    continue
                if in_double:
                    if ch == '"':
                        in_double = False
                    k += 1
                    continue
                if ch == "'":
                    in_single = True
                    k += 1
                    continue
                if ch == '"':
                    in_double = True
                    k += 1
                    continue
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if depth != 0:
                out_parts.append(code[j:k])
                i = k
                continue
            inner = code[j + len(needle) : k]
            replacement = format_fn(inner.strip())
            out_parts.append(replacement)
            i = k + 1
        return "".join(out_parts)

    def _transform_assertions_string_based(self, code: str) -> str:
        """Transform unittest assertion methods using string replacement."""
        import re

        # Use balanced/safe replacements to avoid corrupting nested expressions
        def _fmt_eq(a: str, b: str) -> str:
            return f"assert {a} == {b}"

        code = self._safe_replace_two_arg_call(code, "assertEqual", _fmt_eq)
        code = self._safe_replace_two_arg_call(code, "assertEquals", _fmt_eq)
        code = self._safe_replace_two_arg_call(code, "assertNotEqual", lambda a, b: f"assert {a} != {b}")
        code = self._safe_replace_two_arg_call(code, "assertNotEquals", lambda a, b: f"assert {a} != {b}")
        code = self._safe_replace_one_arg_call(code, "assertTrue", lambda a: f"assert {a}")
        code = self._safe_replace_one_arg_call(code, "assertIsTrue", lambda a: f"assert {a}")
        code = self._safe_replace_one_arg_call(code, "assertFalse", lambda a: f"assert not {a}")
        code = self._safe_replace_one_arg_call(code, "assertIsFalse", lambda a: f"assert not {a}")
        code = self._safe_replace_two_arg_call(code, "assertIs", lambda a, b: f"assert {a} is {b}")
        code = self._safe_replace_two_arg_call(code, "assertIsNot", lambda a, b: f"assert {a} is not {b}")
        code = self._safe_replace_one_arg_call(code, "assertIsNone", lambda a: f"assert {a} is None")
        code = self._safe_replace_one_arg_call(code, "assertIsNotNone", lambda a: f"assert {a} is not None")
        code = self._safe_replace_two_arg_call(code, "assertIn", lambda a, b: f"assert {a} in {b}")
        code = self._safe_replace_two_arg_call(code, "assertNotIn", lambda a, b: f"assert {a} not in {b}")
        code = self._safe_replace_two_arg_call(code, "assertIsInstance", lambda a, b: f"assert isinstance({a}, {b})")
        code = self._safe_replace_two_arg_call(
            code, "assertNotIsInstance", lambda a, b: f"assert not isinstance({a}, {b})"
        )
        for fn in [
            "assertDictEqual",
            "assertDictEquals",
            "assertListEqual",
            "assertListEquals",
            "assertSetEqual",
            "assertSetEquals",
            "assertTupleEqual",
            "assertTupleEquals",
            "assertSequenceEqual",
            "assertMultiLineEqual",
        ]:
            code = self._safe_replace_two_arg_call(code, fn, _fmt_eq)

        # Safe replacement for assertCountEqual(a, b) -> assert sorted(a) == sorted(b)
        def _fmt_count_equal(a: str, b: str) -> str:
            return f"assert sorted({a}) == sorted({b})"

        code = self._safe_replace_two_arg_call(code, "assertCountEqual", _fmt_count_equal)

        # Normalize test method names according to prefixes (basic heuristic)
        # Convert def <prefix>something to def <prefix>_something (avoid double underscores)
        def _normalize_name(m: re.Match[str]) -> str:
            name = m.group(1)
            rest = m.group(2)
            # Insert underscore if missing between prefix and rest
            if rest and not rest.startswith("_"):
                normalized = f"{name}_{rest}"
            else:
                normalized = f"{name}{rest}"
            # Collapse multiple underscores
            normalized = re.sub(r"__+", "_", normalized)
            # Ensure valid identifier chars
            normalized = re.sub(r"[^0-9a-zA-Z_]", "_", normalized)
            return f"def {normalized}(self)"

        # Build dynamic pattern from configured prefixes
        prefixes = "|".join(map(re.escape, getattr(self, "test_prefixes", ["test"])))
        code = re.sub(rf"def\s+({prefixes})([^\s(]*)\(self\)", _normalize_name, code)

        # Transform exception assertions (basic transformation for now)
        code = re.sub(r"self\.assertRaises\s*\(\s*([^,]+)\s*\)", r"pytest.raises(\1)", code)
        code = re.sub(r"self\.assertRaisesRegex\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)", r"pytest.raises(\1)", code)
        code = re.sub(r"self\.assertRaisesRegexp\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)", r"pytest.raises(\1)", code)

        # Transform unittest.main() calls
        code = re.sub(r"unittest\.main\s*\(\s*\)", r"pytest.main()", code)

        return code

    def _transform_fixtures_string_based(self, code: str) -> str:
        """Transform setUp/tearDown methods using string replacement."""
        import re

        # Transform setUp method to setup_method fixture
        setup_pattern = r"(\s+)def setUp\(self\):(.*?)(?=\n\s*def|\n\s*@|\nclass|\nif __name__|\Z)"

        def setup_replacement(match: re.Match[str]) -> str:
            indent = match.group(1)
            setup_body = match.group(2)
            if setup_body.strip():
                return f"{indent}@pytest.fixture\n{indent}def setup_method(self):\n{setup_body}{indent}    yield\n"
            else:
                return f"{indent}@pytest.fixture\n{indent}def setup_method(self):\n{indent}    pass\n{indent}    yield\n{indent}    pass\n"

        code = re.sub(setup_pattern, setup_replacement, code, flags=re.MULTILINE | re.DOTALL)

        # Remove tearDown method (we model teardown via yield in setup fixture)
        teardown_pattern = r"(\s+)def tearDown\(self\):(.*?)(?=\n\s*def|\n\s*@|\nclass|\nif __name__|\Z)"

        def teardown_replacement(match: re.Match[str]) -> str:
            return ""

        code = re.sub(teardown_pattern, teardown_replacement, code, flags=re.MULTILINE | re.DOTALL)

        # Note: setUpClass and tearDownClass transformations are complex and may not work perfectly
        # with regex patterns. For now, we'll leave them as-is or handle them manually.
        # These can be enhanced in future versions with more sophisticated CST-based transformations.

        return code

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
