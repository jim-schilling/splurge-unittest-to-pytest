"""Fixture creator helpers used by the staged converter.

Functions to build pytest fixture function nodes from inferred setup
assignments. The helpers return :class:`libcst.FunctionDef` nodes that
can be inserted into modules by the fixture-injection stage. They are
designed to be small, testable, and side-effect free.

Publics:
    create_fixture_with_cleanup: Build a fixture function that yields with cleanup.
    create_simple_fixture: Build a fixture that returns a simple value.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

import libcst as cst

__all__: list[str] = [
    "create_fixture_with_cleanup",
    "create_simple_fixture",
    "parse_setup_assignments",
]


from .setup_parser import parse_setup_assignments

DOMAINS = ["converter", "fixtures"]


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

    # Normalize the emitted fixture function name by stripping leading
    # underscores from the original attribute name. This produces more
    # readable fixture names for integration golden files while keeping the
    # internal binding deterministic. For the internal temporary binding we
    # use two strategies:
    # - If the original attribute name started with an underscore, prefer
    #   a readable '<name>_instance' base (e.g., '_resource' -> 'resource_instance')
    #   which matches existing integration golden expectations.
    # - Otherwise, preserve the legacy underscore-prefixed base '_<attr>_value'
    #   so unit tests that relied on that pattern continue to pass.
    func_name = attr_name.lstrip("_")
    if attr_name.startswith("_"):
        base_name = f"{func_name}_instance"
    else:
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

    # Replace references to both the normalized attr name and any leading-underscore
    # module-level variant (e.g., 'resource' and '_resource') so cleanup code that
    # referenced a module var will be updated to the local binding. This also
    # handles cleanup code that used the module-level name with a leading
    # underscore.
    from .name_replacer import replace_names_in_statements

    # Cleanup statements may already have been normalized by earlier stages
    # (e.g., converted '_resource' -> 'resource'). Replace both the
    # normalized form (no leading underscores) and the original raw form
    # so we correctly update references to the local binding.
    normalized_name = attr_name.lstrip("_")
    safe_cleanup = replace_names_in_statements(cleanup_statements, normalized_name, value_name)
    # also replace raw leading-underscore form if present and different
    if normalized_name != attr_name:
        safe_cleanup = replace_names_in_statements(safe_cleanup, attr_name, value_name)

    # If the value expression is a simple literal/container/comprehension and
    # the cleanup statements do not reference the attribute, prefer yielding
    # the literal expression directly rather than binding it to a local name.
    # This produces canonical fixtures like `yield 42` which match golden
    # expectations when cleanup does not need the local binding.
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

    # Prefer yielding the literal directly when the value is simple and the
    # cleanup statements do not reference the attribute. If cleanup refers to
    # the attribute (e.g., cleanup(self.x) or cleanup(x)), we must bind the
    # value to a local and update cleanup references to that local so the
    # cleanup operates on the correct object.
    # If there are cleanup statements, we must bind the value to a local so
    # the cleanup can reference that local. Only when there are no cleanup
    # statements and the value is a simple literal/container do we emit a
    # direct `yield <literal>` to keep fixtures canonical.
    # Determine whether cleanup statements are trivial nullifications of
    # the attribute (e.g., `self.x = None` or `x = None`). In those cases
    # the cleanup does not need access to the yielded value and we can
    # prefer yielding the literal directly and then emit the cleanup
    # statements after the yield. This preserves golden output like
    # `yield 42` while still translating `self.x = None` -> `x = None`.
    def _cleanup_is_trivial_nullifying(stmts: list[cst.BaseStatement], attr: str) -> bool:
        for st in stmts:
            # expect simple assignment statements
            if not isinstance(st, cst.SimpleStatementLine):
                return False
            try:
                inner = st.body[0]
            except Exception:
                return False
            if not isinstance(inner, cst.Assign):
                return False
            # accept target forms: Name(attr) or Attribute(Name('self'), attr)
            tgt = inner.targets[0].target
            valid_target = False
            if isinstance(tgt, cst.Name) and tgt.value == attr:
                valid_target = True
            if (
                isinstance(tgt, cst.Attribute)
                and isinstance(getattr(tgt, "value", None), cst.Name)
                and getattr(tgt.attr, "value", None) == attr
            ):
                # allow self.attr assignments
                if getattr(tgt.value, "value", None) in ("self", "cls"):
                    valid_target = True
            if not valid_target:
                return False
            # right-hand side should be a simple Name('None') to be considered
            val = inner.value
            if not (isinstance(val, cst.Name) and getattr(val, "value", None) == "None"):
                return False
        return True

    if cleanup_statements:
        # If cleanup only nullifies the attribute, prefer direct yield
        # followed by the translated cleanup statements.
        if _cleanup_is_trivial_nullifying(cleanup_statements, normalized_name) and _is_simple_value(value_expr):
            yield_direct = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=value_expr))])
            body = cst.IndentedBlock(body=[yield_direct] + safe_cleanup)
        else:
            body = cst.IndentedBlock(body=[value_assign, yield_stmt] + safe_cleanup)
    else:
        if _is_simple_value(value_expr):
            yield_direct = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=value_expr))])
            body = cst.IndentedBlock(body=[yield_direct])
        else:
            body = cst.IndentedBlock(body=[value_assign, yield_stmt])

    fixture_func = cst.FunctionDef(
        name=cst.Name(func_name),
        params=cst.Parameters(),
        body=body,
        decorators=[fixture_decorator],
        # Do not set a return annotation for yield-style fixtures; this
        # avoids introducing a typing import (e.g., Generator) into the
        # module when not desired by golden files.
        returns=None,
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
        func_name = attr_name.lstrip("_")
        fixture_func = cst.FunctionDef(
            name=cst.Name(func_name),
            params=cst.Parameters(),
            body=body,
            decorators=[fixture_decorator],
            returns=_infer_simple_return_annotation(value_expr),
            asynchronous=None,
        )
        return fixture_func

    # fallback: bind to a local name and return it. Use the same underscore-
    # prefixed base name convention used by the cleanup fixture creator so
    # downstream tests and consumers can rely on a deterministic pattern.
    base_name = f"_{attr_name}_value"
    # avoid colliding with common reserved names
    reserved = {"request", "tmp_path", attr_name, base_name}
    value_name = _choose_unique_name(base_name, reserved)
    value_assign = cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(value_name))], value=value_expr)]
    )
    return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(value_name))])
    body = cst.IndentedBlock(body=[value_assign, return_stmt])

    func_name = attr_name.lstrip("_")
    fixture_func = cst.FunctionDef(
        name=cst.Name(func_name),
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
    attr_name: str,
    *,
    content_fixture_name: str | None = None,
    filename: str | None = None,
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
    path_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name("path"))],
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
                value=cst.Call(func=cst.Attribute(value=cst.Name("path"), attr=cst.Name("write_text")), args=write_args)
            )
        ]
    )

    # return str(p)
    return_stmt = cst.SimpleStatementLine(
        body=[cst.Return(value=cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("path"))]))]
    )

    params = [cst.Param(name=cst.Name("tmp_path"))]
    if content_fixture_name:
        params.append(cst.Param(name=cst.Name(content_fixture_name)))

    body = cst.IndentedBlock(body=[path_assign, write_call, return_stmt])

    fixture_func = cst.FunctionDef(
        name=cst.Name(attr_name),
        params=cst.Parameters(params=params),
        body=body,
        decorators=[fixture_decorator],
        returns=cst.Annotation(annotation=cst.Name("str")),
    )

    return fixture_func


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
