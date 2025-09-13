"""Fixture helper creators extracted from the monolithic converter.

These functions are pure-ish: they accept the needed inputs and return libcst
nodes. The class in `converter.py` keeps thin wrappers that manage transformer
state (e.g., setting self.needs_pytest_import) and call these helpers.
"""

from typing import Any

import libcst as cst

__all__: list[str] = [
    "create_fixture_with_cleanup",
    "create_simple_fixture",
    "parse_setup_assignments",
]

from .setup_parser import parse_setup_assignments


def _collect_identifiers_from_statements(stmts: list[cst.BaseStatement]) -> set[str]:
    ids: set[str] = set()

    class _NameCollector(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> None:
            ids.add(node.value)

    for s in stmts:
        try:
            s.visit(_NameCollector())
        except Exception:
            continue
    return ids


def _choose_unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    i = 1
    while True:
        cand = f"{base}_{i}"
        if cand not in existing:
            return cand
        i += 1


def _infer_simple_return_annotation(expr: cst.BaseExpression | None) -> cst.Annotation | None:
    """Infer a lightweight return annotation for very simple expressions.

    This is intentionally conservative: it only handles plain literals and
    container literals and returns a simple `cst.Annotation` referencing a
    builtin or typing name (e.g., `int`, `str`, `List`). More complex
    inference is left to the generator stage which has broader context.
    """
    if expr is None:
        return None
    # primitives
    if isinstance(expr, cst.Integer):
        return cst.Annotation(annotation=cst.Name("int"))
    if isinstance(expr, cst.Float):
        return cst.Annotation(annotation=cst.Name("float"))
    if isinstance(expr, cst.SimpleString):
        return cst.Annotation(annotation=cst.Name("str"))
    # container literals -> use typing names (List/Dict/Set/Tuple)
    if isinstance(expr, cst.List):
        return cst.Annotation(annotation=cst.Name("List"))
    if isinstance(expr, cst.Tuple):
        return cst.Annotation(annotation=cst.Name("Tuple"))
    if isinstance(expr, cst.Set):
        return cst.Annotation(annotation=cst.Name("Set"))
    if isinstance(expr, cst.Dict):
        return cst.Annotation(annotation=cst.Name("Dict"))
    # comprehensions and simple names are not annotated here
    return None


def create_fixture_with_cleanup(
    attr_name: str, value_expr: cst.BaseExpression, cleanup_statements: list[cst.BaseStatement]
) -> cst.FunctionDef:
    """Create a fixture with yield pattern and cleanup.

    This mirrors the logic previously inside UnittestToPytestTransformer._create_fixture_with_cleanup.
    """
    from .decorators import build_pytest_fixture_decorator

    fixture_decorator = build_pytest_fixture_decorator()

    # Always create a local value name and assign the value_expr to it. This
    # ensures cleanup statements can reliably reference the local variable
    # rather than the original attribute name.
    # pick a deterministic base and ensure it doesn't collide with names used
    base_name = f"_{attr_name}_value"
    existing_names = _collect_identifiers_from_statements(cleanup_statements)
    value_name = _choose_unique_name(base_name, existing_names)
    value_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value_name))],
                value=value_expr,
            )
        ]
    )
    # Yield the local value name so fixtures follow the yield pattern.
    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=cst.Name(value_name)))])

    # Replace references to attr_name within cleanup_statements with the local value_name
    from .name_replacer import replace_names_in_statements

    safe_cleanup = replace_names_in_statements(cleanup_statements, attr_name, value_name)

    body = cst.IndentedBlock(body=[value_assign, yield_stmt] + safe_cleanup)

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[fixture_decorator],
        returns=_infer_simple_return_annotation(value_expr),
        asynchronous=None,
    )

    return fixture_func


def create_simple_fixture(attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
    """Create a simple fixture with return (no cleanup needed)."""
    from .decorators import build_pytest_fixture_decorator

    fixture_decorator = build_pytest_fixture_decorator()

    # If the value expression is a simple literal, container literal, or
    # comprehension, return it directly to produce a canonical fixture
    # shape (no temporary binding). Otherwise, bind to a local and return.
    def _is_simple_value(expr: cst.BaseExpression | None) -> bool:
        if expr is None:
            return False
        if isinstance(expr, (cst.Integer, cst.Float, cst.Imaginary, cst.SimpleString, cst.Name)):
            return True
        if isinstance(expr, (cst.List, cst.Tuple, cst.Set, cst.Dict)):
            return True
        cls = getattr(expr, "__class__", None)
        if cls is not None and getattr(cls, "__name__", "").endswith("Comp"):
            return True
        return False

    if _is_simple_value(value_expr):
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=value_expr)])
        body = cst.IndentedBlock(body=[return_stmt])
        fixture_func = cst.FunctionDef(
            name=cst.Name(attr_name),
            params=cst.Parameters(),
            body=body,
            decorators=[fixture_decorator],
            returns=_infer_simple_return_annotation(value_expr),
            asynchronous=None,
        )
        return fixture_func

    # fallback: bind to a local name and return it
    base_name = f"_{attr_name}_value"
    # avoid colliding with common reserved names
    reserved = {"request", "tmp_path", attr_name}
    value_name = _choose_unique_name(base_name, reserved)
    value_assign = cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(value_name))], value=value_expr)]
    )
    return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(value_name))])
    body = cst.IndentedBlock(body=[value_assign, return_stmt])

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(),
        body=body,
        decorators=[fixture_decorator],
        returns=None,
        asynchronous=None,
    )

    return fixture_func


def _is_self_referential(expr: cst.BaseExpression, attr_name: str) -> bool:
    """Return True if the expression is a trivial self-referential placeholder
    like `sql_file` or `self.sql_file` which indicates the converter couldn't
    infer how to build the artifact.
    """

    # Recursively inspect common expression shapes for a trivial reference to
    # the attribute. We treat Name(attr) and Attribute(self, attr) as
    # self-referential. Additionally, accept simple wrappers like
    # `str(attr)` or other Call forms whose arguments contain such a name.
    def _inner(e: cst.BaseExpression | None) -> bool:
        try:
            if e is None:
                return False
            # direct name like `sql_file`
            if isinstance(e, cst.Name):
                return e.value == attr_name
            # attribute like self.sql_file or cls.sql_file
            if isinstance(e, cst.Attribute) and isinstance(e.value, cst.Name) and e.value.value in ("self", "cls"):
                if isinstance(e.attr, cst.Name) and e.attr.value == attr_name:
                    return True
                # if attribute chains like self.x.y, still not our target
                return False
            # Call: inspect func and args for inner reference
            if isinstance(e, cst.Call):
                # check args
                for a in e.args:
                    if _inner(getattr(a, "value", None)):
                        return True
                # also check the callable itself in case of partials/aliases
                return _inner(getattr(e, "func", None))
            # Subscript: inspect value and slices
            if isinstance(e, cst.Subscript):
                if _inner(getattr(e, "value", None)):
                    return True
                for s in getattr(e, "slice", []) or []:
                    inner = getattr(s, "slice", None) or getattr(s, "value", None) or s
                    if isinstance(inner, cst.BaseExpression) and _inner(inner):
                        return True
                return False
            # Tuples/Lists/Sets: inspect elements
            if isinstance(e, (cst.Tuple, cst.List, cst.Set)):
                for el in getattr(e, "elements", []) or []:
                    val = getattr(el, "value", el)
                    if isinstance(val, cst.BaseExpression) and _inner(val):
                        return True
                return False
        except Exception:
            # be conservative on unexpected shapes
            return False
        return False

    return _inner(expr)


def create_simple_fixture_with_guard(attr_name: str, value_expr: cst.BaseExpression) -> cst.FunctionDef:
    """Create a simple fixture but detect self-referential placeholder expressions.

    If a placeholder is detected, emit a fixture that raises a clear runtime
    error telling the maintainer to implement the fixture manually or provide
    a helper that the converter can call (safer than emitting a broken placeholder).
    """
    # If the value expression is trivial and self-referential, emit a guard that
    # raises an informative error at runtime. The staged pipeline's generator
    # will attempt autocreation of tmp_path-backed fixtures when a sibling
    # '<prefix>_content' fixture is present; this helper remains conservative
    # and emits a guard to avoid producing silently-broken placeholders.
    if _is_self_referential(value_expr, attr_name):
        from .decorators import build_pytest_fixture_decorator

        fixture_decorator = build_pytest_fixture_decorator()
        err_msg = (
            f"Converted fixture '{attr_name}' is ambiguous: converter produced a "
            "self-referential placeholder. Please implement this fixture to create "
            "the required artifact (e.g., using tmp_path and helper factories)."
        )
        body = cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(
                    body=[
                        cst.Raise(
                            exc=cst.Call(
                                func=cst.Name("RuntimeError"), args=[cst.Arg(value=cst.SimpleString(repr(err_msg)))]
                            )
                        )
                    ]
                )
            ]
        )

        fixture_func = cst.FunctionDef(
            name=cst.Name(attr_name),
            params=cst.Parameters(),
            body=body,
            decorators=[fixture_decorator],
        )
        return fixture_func

    # fallback to normal behavior when not self-referential
    return create_simple_fixture(attr_name, value_expr)


def create_autocreated_file_fixture(
    attr_name: str, content_fixture_name: str | None = None, filename: str | None = None
) -> cst.FunctionDef:
    """Create a fixture that generates a file under pytest's tmp_path using
    content from a sibling fixture (e.g., `sql_content`) when available.

    This is conservative but useful for common patterns where setUp created a
    temporary file from in-memory content and then assigned `self.sql_file = str(sql_file)`.
    The generated fixture will accept `tmp_path` and optionally the content
    fixture, write the content to a created file, and return the string path.
    """
    from .decorators import build_pytest_fixture_decorator

    fixture_decorator = build_pytest_fixture_decorator()

    # Determine filename: prefer provided filename, otherwise fallback to '<attr_name>.sql'
    if filename:
        filename_val = filename
    else:
        filename_val = f"{attr_name}.sql"
    p_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("p"))],
                value=cst.Call(
                    func=cst.Attribute(value=cst.Name("tmp_path"), attr=cst.Name("joinpath")),
                    args=[cst.Arg(value=cst.SimpleString(repr(filename_val)))],
                ),
            )
        ]
    )

    # p.write_text(content_fixture_name or '')
    write_args = (
        [cst.Arg(value=cst.Name(content_fixture_name))]
        if content_fixture_name
        else [cst.Arg(value=cst.SimpleString("''"))]
    )
    write_call = cst.SimpleStatementLine(
        body=[
            cst.Expr(
                value=cst.Call(func=cst.Attribute(value=cst.Name("p"), attr=cst.Name("write_text")), args=write_args)
            )
        ]
    )

    # return str(p)
    return_stmt = cst.SimpleStatementLine(
        body=[cst.Return(value=cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("p"))]))]
    )

    params = [cst.Param(name=cst.Name("tmp_path"))]
    if content_fixture_name:
        params.append(cst.Param(name=cst.Name(content_fixture_name)))

    body = cst.IndentedBlock(body=[p_assign, write_call, return_stmt])

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(params=params),
        body=body,
        decorators=[fixture_decorator],
        returns=cst.Annotation(annotation=cst.Name("str")),
    )

    return fixture_func


def make_autouse_attach_to_instance_fixture(setup_fixtures: dict[str, cst.FunctionDef]) -> cst.FunctionDef:
    """Create an autouse fixture function that attaches named fixtures to unittest-style test instances.

    Returns a libcst.FunctionDef for:
        @pytest.fixture(autouse=True)
        def _attach_to_instance(request):
            inst = getattr(request, 'instance', None)
            if inst is not None:
                setattr(inst, 'name', name)  # for each fixture name
    """
    # Build inst = getattr(request, 'instance', None)
    inst_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("inst"))],
                value=cst.Call(
                    func=cst.Name("getattr"),
                    args=[
                        cst.Arg(value=cst.Name("request")),
                        cst.Arg(value=cst.SimpleString("'instance'")),
                        cst.Arg(value=cst.Name("None")),
                    ],
                ),
            )
        ]
    )

    set_calls: list[cst.BaseStatement] = []
    for name in setup_fixtures.keys():
        set_calls.append(
            cst.SimpleStatementLine(
                body=[
                    cst.Expr(
                        value=cst.Call(
                            func=cst.Name("setattr"),
                            args=[
                                cst.Arg(value=cst.Name("inst")),
                                cst.Arg(value=cst.SimpleString(f"'{name}'")),
                                cst.Arg(value=cst.Name(name)),
                            ],
                        )
                    )
                ]
            )
        )

    if_block = cst.IndentedBlock(body=set_calls)
    if_stmt = cst.If(
        test=cst.Comparison(
            left=cst.Name("inst"), comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]
        ),
        body=if_block,
    )

    from .decorators import build_pytest_fixture_decorator

    decorator = build_pytest_fixture_decorator({"autouse": True})

    func = cst.FunctionDef(
        name=cst.Name("_attach_to_instance"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name("request"))]),
        body=cst.IndentedBlock(body=[inst_assign, if_stmt]),
        decorators=[decorator],
    )

    return func


def add_autouse_attach_fixture_to_module(
    module_node: cst.Module, setup_fixtures: dict[str, cst.FunctionDef]
) -> cst.Module:
    """Insert the autouse attachment fixture into the module (after pytest import if present)."""
    if not setup_fixtures:
        return module_node

    func = make_autouse_attach_to_instance_fixture(setup_fixtures)

    new_body: list[Any] = list(module_node.body)
    insert_pos = 0
    for i, stmt in enumerate(new_body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.Import):
                for alias in first.names:
                    if isinstance(alias.name, cst.Name) and alias.name.value == "pytest":
                        insert_pos = i + 1
                        break
            if insert_pos:
                break

    new_body.insert(insert_pos, cst.EmptyLine())
    new_body.insert(insert_pos + 1, func)

    return module_node.with_changes(body=new_body)


def create_fixture_for_attribute(
    attr_name: str, value_expr: cst.BaseExpression, teardown_cleanup: dict[str, list[cst.BaseStatement]]
) -> cst.FunctionDef:
    """Create fixture for attribute (delegates to cleanup/simple creators)."""
    cleanup_statements = teardown_cleanup.get(attr_name, [])
    if cleanup_statements:
        return create_fixture_with_cleanup(attr_name, value_expr, cleanup_statements)
    # Use guarded simple fixture creator which handles ambiguous self-referential
    # placeholders conservatively (emit a runtime guard) or creates a safe
    # tmp_path-based fixture when appropriate.
    try:
        return create_simple_fixture_with_guard(attr_name, value_expr)
    except NameError:
        # Fallback in case the guarded creator isn't available in this import
        return create_simple_fixture(attr_name, value_expr)
