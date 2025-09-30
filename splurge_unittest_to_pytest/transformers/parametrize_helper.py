"""Helpers for converting subTest-based loops into pytest parametrization.

This module centralizes the logic for rewriting ``for`` loops that wrap
``with self.subTest(...)`` blocks into ``pytest.mark.parametrize``
decorators. The helpers favour a conservative, domain-agnostic approach:
only literal iterables (lists/tuples), references to prior literal
assignments, and ``range`` calls with static arguments are eligible.

When conversion succeeds the helper returns an updated ``FunctionDef``
with a new parametrization decorator, loop-target parameters added to the
function signature, and the subTest body lifted into the function body.

All helpers in this module work purely with libcst nodes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import cast

import libcst as cst

DOMAINS = ["transformers", "parametrize"]
__all__ = ["convert_subtest_loop_to_parametrize"]


class ParametrizeConversionError(Exception):
    """Raised when a subTest loop cannot be safely converted."""


@dataclass(frozen=True)
class _SubtestLoop:
    index: int
    loop: cst.For
    with_stmt: cst.With
    call: cst.Call
    body: cst.IndentedBlock


def convert_subtest_loop_to_parametrize(
    original_func: cst.FunctionDef,
    updated_func: cst.FunctionDef,
    transformer,
) -> cst.FunctionDef | None:
    """Return a parametrized ``FunctionDef`` when a simple subTest loop is detected.

    Args:
        original_func: Function definition prior to other transformations (unused).
        updated_func: Function definition to analyse and potentially rewrite.
        transformer: Transformer instance used to record side effects such as
            ``needs_pytest_import``.

    Returns:
        Updated function definition with a parametrization decorator when
        conversion succeeds, otherwise ``None``.
    """

    try:
        # libcst exposes nodes as CSTNode; narrow the type to BaseStatement so
        # static type checkers (mypy) accept passing this list to helper
        # functions typed to accept Sequence[cst.BaseStatement]. We keep a
        # concrete list for indexing and slicing below.
        body_statements: list[cst.BaseStatement] = cast(list[cst.BaseStatement], list(updated_func.body.body))
        subtest_loop = _find_subtest_loop(body_statements)
        if subtest_loop is None:
            return None

        param_names = _extract_target_names(subtest_loop.loop.target)
        if not param_names:
            return None

        _validate_inner_body(subtest_loop.body)
        _validate_subtest_call(subtest_loop.call, param_names)

        rows, removable_indexes = _extract_iter_rows(
            subtest_loop.loop.iter,
            body_statements,
            subtest_loop.index,
            len(param_names),
        )
        if not rows:
            return None

        include_ids = getattr(transformer, "parametrize_include_ids", True)
        add_annotations = getattr(transformer, "parametrize_add_annotations", True)

        decorator = _build_decorator(param_names, rows, include_ids)
        annotations = _infer_param_annotations(rows) if add_annotations else tuple(None for _ in param_names)
        new_params = _ensure_function_params(updated_func.params, param_names, annotations)
        new_body = _build_new_body(body_statements, subtest_loop, removable_indexes)

        existing_decorators = list(updated_func.decorators or [])
        if any(_is_parametrize_decorator(deco) for deco in existing_decorators):
            return None

        transformer.needs_pytest_import = True

        return updated_func.with_changes(
            decorators=[decorator, *existing_decorators],
            params=new_params,
            body=cst.IndentedBlock(body=new_body),
        )
    except ParametrizeConversionError:
        return None


def _find_subtest_loop(statements: Sequence[cst.BaseStatement]) -> _SubtestLoop | None:
    for index, stmt in enumerate(statements):
        if not isinstance(stmt, cst.For):
            continue
        body = stmt.body
        if not isinstance(body, cst.IndentedBlock) or len(body.body) != 1:
            continue
        inner_stmt = body.body[0]
        if not isinstance(inner_stmt, cst.With):
            continue
        if len(inner_stmt.items) != 1:
            continue
        with_item = inner_stmt.items[0]
        if not isinstance(with_item.item, cst.Call):
            continue
        call = with_item.item
        func = call.func
        if not isinstance(func, cst.Attribute):
            continue
        if not isinstance(func.value, cst.Name):
            continue
        if func.value.value not in {"self", "cls"}:
            continue
        if func.attr.value != "subTest":
            continue
        if inner_stmt.body is None or not isinstance(inner_stmt.body, cst.IndentedBlock):
            continue
        return _SubtestLoop(index=index, loop=stmt, with_stmt=inner_stmt, call=call, body=inner_stmt.body)
    return None


def _extract_target_names(target: cst.BaseAssignTargetExpression) -> tuple[str, ...]:
    if isinstance(target, cst.Name):
        return (target.value,)
    if isinstance(target, cst.Tuple):
        names: list[str] = []
        for element in target.elements:
            if not isinstance(element, cst.Element):
                return ()
            value = element.value
            if not isinstance(value, cst.Name):
                return ()
            names.append(value.value)
        return tuple(names)
    return ()


def _validate_inner_body(body: cst.IndentedBlock) -> None:
    for stmt in body.body:
        if isinstance(stmt, cst.If):
            continue
        if isinstance(stmt, cst.SimpleStatementLine):
            if len(stmt.body) != 1:
                raise ParametrizeConversionError
            inner_stmt = stmt.body[0]
            if isinstance(inner_stmt, cst.Return):
                raise ParametrizeConversionError
            continue
        raise ParametrizeConversionError


def _validate_subtest_call(call: cst.Call, target_names: Sequence[str]) -> None:
    names = set(target_names)
    referenced: set[str] = set()
    has_positional = False
    has_keyword = False

    positional_count = 0

    for arg in call.args:
        if arg.keyword is None:
            has_positional = True
            positional_count += 1
            if positional_count > 1:
                raise ParametrizeConversionError
            value = arg.value
            refs = _collect_name_values(value, names)
            if not refs:
                raise ParametrizeConversionError
            referenced.update(refs)
            continue

        has_keyword = True
        if not isinstance(arg.keyword, cst.Name):
            raise ParametrizeConversionError

        value = arg.value
        refs = _collect_name_values(value, names)
        if not refs:
            raise ParametrizeConversionError
        referenced.update(refs)

    if not referenced or (has_positional and has_keyword):
        raise ParametrizeConversionError


def _extract_iter_rows(
    iter_node: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
    arity: int,
) -> tuple[tuple[tuple[cst.BaseExpression, ...], ...], tuple[int, ...]]:
    values, removable_indexes = _resolve_rows_from_iterable(iter_node, statements, loop_index)

    rows: list[tuple[cst.BaseExpression, ...]] = []
    for value in values:
        row = _normalize_iter_value(value, arity)
        if row is None:
            raise ParametrizeConversionError
        rows.append(row)

    return tuple(rows), tuple(sorted(removable_indexes))


def _resolve_rows_from_iterable(
    iter_node: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[int, ...]]:
    literal_values = _extract_literal_elements(iter_node)
    if literal_values is not None:
        return literal_values, ()

    if _is_range_call(iter_node):
        return _range_values(iter_node), ()

    if isinstance(iter_node, cst.Name):
        resolution = _resolve_name_reference(iter_node.value, statements, loop_index)
        if resolution is None:
            raise ParametrizeConversionError
        values, removable_index = resolution
        return values, (removable_index,)

    if isinstance(iter_node, cst.Call):
        call_result = _extract_call_iter_rows(iter_node, statements, loop_index)
        if call_result is not None:
            return call_result

    raise ParametrizeConversionError


def _extract_call_iter_rows(
    call: cst.Call,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[int, ...]] | None:
    func = call.func

    if isinstance(func, cst.Name) and func.value == "enumerate":
        return _build_enumerate_rows(call, statements, loop_index)

    if isinstance(func, cst.Attribute):
        method_name = func.attr.value if isinstance(func.attr, cst.Name) else None
        if method_name in {"items", "keys", "values"}:
            return _build_mapping_rows(func.value, method_name, call.args, statements, loop_index)

    return None


def _extract_literal_elements(node: cst.BaseExpression) -> tuple[cst.BaseExpression, ...] | None:
    if isinstance(node, cst.List | cst.Tuple):
        elements: list[cst.BaseExpression] = []
        for element in node.elements:
            if not isinstance(element, cst.Element):
                return None
            elements.append(element.value)
        return tuple(elements)
    return None


def _is_range_call(node: cst.BaseExpression) -> bool:
    if not isinstance(node, cst.Call):
        return False
    if not isinstance(node.func, cst.Name):
        return False
    return node.func.value == "range"


def _range_values(node: cst.BaseExpression) -> tuple[cst.BaseExpression, ...]:
    if not isinstance(node, cst.Call):
        raise ParametrizeConversionError

    args: list[int] = []
    for arg in node.args:
        if not isinstance(arg.value, cst.Integer):
            raise ParametrizeConversionError
        try:
            args.append(int(arg.value.value))
        except Exception as exc:  # pragma: no cover - defensive
            # Integer parsing could in theory fail; wrap to uniform error type
            raise ParametrizeConversionError from exc

    start, stop, step = _normalize_range_args(args)
    rng = list(range(start, stop, step))
    if len(rng) > 20:
        raise ParametrizeConversionError
    return tuple(cst.Integer(value=str(value)) for value in rng)


def _normalize_range_args(args: Sequence[int]) -> tuple[int, int, int]:
    if len(args) == 1:
        return 0, args[0], 1
    if len(args) == 2:
        return args[0], args[1], 1
    if len(args) == 3:
        return args[0], args[1], args[2]
    raise ParametrizeConversionError


def _resolve_name_reference(
    name: str,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], int] | None:
    for idx in range(loop_index - 1, -1, -1):
        stmt = statements[idx]
        if isinstance(stmt, cst.SimpleStatementLine):
            for small_stmt in stmt.body:
                if isinstance(small_stmt, cst.Assign):
                    if len(small_stmt.targets) != 1:
                        continue
                    target = small_stmt.targets[0].target
                    if isinstance(target, cst.Name) and target.value == name:
                        elements = _extract_literal_elements(small_stmt.value)
                        if elements is not None:
                            return elements, idx
    return None


def _normalize_iter_value(value: cst.BaseExpression, arity: int) -> tuple[cst.BaseExpression, ...] | None:
    if arity == 1:
        return (value.deep_clone(),)

    if isinstance(value, cst.Tuple | cst.List):
        extracted: list[cst.BaseExpression] = []
        for element in value.elements:
            if not isinstance(element, cst.Element):
                return None
            extracted.append(element.value.deep_clone())
        if len(extracted) != arity:
            return None
        return tuple(extracted)

    return None


def _build_enumerate_rows(
    call: cst.Call,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[int, ...]]:
    if not call.args:
        raise ParametrizeConversionError

    iterable_arg: cst.Arg | None = None
    start_value = 0
    removable_indexes: set[int] = set()

    for arg in call.args:
        if arg.keyword is None:
            if iterable_arg is None:
                iterable_arg = arg
                continue
            start_value = _evaluate_int_literal(arg.value)
            continue

        if not isinstance(arg.keyword, cst.Name) or arg.keyword.value != "start":
            raise ParametrizeConversionError
        start_value = _evaluate_int_literal(arg.value)

    if iterable_arg is None or iterable_arg.value is None:
        raise ParametrizeConversionError

    base_values, indexes = _resolve_sequence_argument(iterable_arg.value, statements, loop_index)
    removable_indexes.update(indexes)

    rows: list[cst.BaseExpression] = []
    current_index = start_value
    for base_value in base_values:
        rows.append(
            cst.Tuple(
                elements=[
                    cst.Element(value=cst.Integer(value=str(current_index))),
                    cst.Element(value=base_value.deep_clone()),
                ]
            )
        )
        current_index += 1

    return tuple(rows), tuple(sorted(removable_indexes))


def _build_mapping_rows(
    base_expr: cst.BaseExpression,
    method_name: str,
    args: Sequence[cst.Arg],
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[int, ...]]:
    if args:
        raise ParametrizeConversionError

    pairs, removable_indexes = _resolve_mapping_argument(base_expr, statements, loop_index)

    rows: list[cst.BaseExpression] = []
    if method_name == "items":
        for key, value in pairs:
            rows.append(
                cst.Tuple(
                    elements=[
                        cst.Element(value=key.deep_clone()),
                        cst.Element(value=value.deep_clone()),
                    ]
                )
            )
    elif method_name == "keys":
        for key, _ in pairs:
            rows.append(key.deep_clone())
    else:
        for _, value in pairs:
            rows.append(value.deep_clone())

    return tuple(rows), tuple(sorted(removable_indexes))


def _resolve_sequence_argument(
    expr: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[int, ...]]:
    literal_values = _extract_literal_elements(expr)
    if literal_values is not None:
        return literal_values, ()

    if isinstance(expr, cst.Name):
        resolution = _resolve_name_reference(expr.value, statements, loop_index)
        if resolution is None:
            raise ParametrizeConversionError
        values, removable_index = resolution
        return values, (removable_index,)

    raise ParametrizeConversionError


def _resolve_mapping_argument(
    expr: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[tuple[cst.BaseExpression, cst.BaseExpression], ...], tuple[int, ...]]:
    direct_pairs = _extract_dict_pairs(expr)
    if direct_pairs is not None:
        return direct_pairs, ()

    if not isinstance(expr, cst.Name):
        raise ParametrizeConversionError

    name = expr.value
    for idx in range(loop_index - 1, -1, -1):
        stmt = statements[idx]
        if not isinstance(stmt, cst.SimpleStatementLine):
            continue
        for small_stmt in stmt.body:
            if not isinstance(small_stmt, cst.Assign):
                continue
            if len(small_stmt.targets) != 1:
                continue
            target = small_stmt.targets[0].target
            if not isinstance(target, cst.Name) or target.value != name:
                continue
            pairs = _extract_dict_pairs(small_stmt.value)
            if pairs is None:
                raise ParametrizeConversionError
            return pairs, (idx,)

    raise ParametrizeConversionError


def _extract_dict_pairs(
    node: cst.BaseExpression,
) -> tuple[tuple[cst.BaseExpression, cst.BaseExpression], ...] | None:
    if not isinstance(node, cst.Dict):
        return None

    pairs: list[tuple[cst.BaseExpression, cst.BaseExpression]] = []
    for element in node.elements:
        if not isinstance(element, cst.DictElement):
            return None
        pairs.append((element.key, element.value))

    return tuple(pairs)


def _evaluate_int_literal(expr: cst.BaseExpression) -> int:
    if not isinstance(expr, cst.Integer):
        raise ParametrizeConversionError

    try:
        return int(expr.value)
    except Exception as exc:  # pragma: no cover - defensive
        raise ParametrizeConversionError from exc


def _build_decorator(
    param_names: tuple[str, ...],
    rows: Sequence[tuple[cst.BaseExpression, ...]],
    include_ids: bool,
) -> cst.Decorator:
    param_arg_value = ",".join(param_names)
    params_arg = cst.Arg(value=cst.SimpleString(value=f'"{param_arg_value}"'))

    list_elements: list[cst.Element] = []
    for row in rows:
        if len(row) == 1:
            list_elements.append(cst.Element(value=row[0].deep_clone()))
        else:
            tuple_expr = cst.Tuple([cst.Element(value=item.deep_clone()) for item in row])
            list_elements.append(cst.Element(value=tuple_expr))
    data_arg = cst.Arg(value=cst.List(elements=list_elements))

    parametrize_call = cst.Call(
        func=cst.Attribute(
            value=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark")),
            attr=cst.Name(value="parametrize"),
        ),
        args=[params_arg, data_arg],
    )

    if include_ids:
        ids_elements = [cst.Element(value=cst.SimpleString(value=f'"row_{index}"')) for index in range(len(rows))]
        ids_arg = cst.Arg(keyword=cst.Name(value="ids"), value=cst.List(elements=ids_elements))
        parametrize_call = parametrize_call.with_changes(args=[*parametrize_call.args, ids_arg])

    return cst.Decorator(decorator=parametrize_call)


def _infer_param_annotations(
    rows: Sequence[tuple[cst.BaseExpression, ...]],
) -> tuple[cst.Annotation | None, ...]:
    if not rows:
        return ()

    columns = list(zip(*rows, strict=False))
    annotations: list[cst.Annotation | None] = []

    for column in columns:
        type_hint = _infer_column_type(column)
        if type_hint is None:
            annotations.append(None)
            continue
        annotations.append(cst.Annotation(annotation=cst.parse_expression(type_hint)))

    return tuple(annotations)


def _infer_column_type(values: Sequence[cst.BaseExpression]) -> str | None:
    inferred: set[str] = set()

    for value in values:
        hint = _infer_expression_type(value)
        if hint is not None:
            inferred.add(hint)

    if not inferred:
        return None
    if len(inferred) == 1:
        return next(iter(inferred))
    return None


def _infer_expression_type(expr: cst.BaseExpression) -> str | None:
    if isinstance(expr, cst.Integer):
        return "int"
    if isinstance(expr, cst.Float):
        return "float"
    if isinstance(expr, cst.SimpleString):
        return "str"
    if isinstance(expr, cst.Name):
        if expr.value in {"True", "False"}:
            return "bool"
    if isinstance(expr, cst.Dict):
        return "dict[str, object]"
    return None


def _ensure_function_params(
    params: cst.Parameters,
    names: Iterable[str],
    annotations: Sequence[cst.Annotation | None],
) -> cst.Parameters:
    existing = list(params.params)
    existing_names = {param.name.value for param in existing if isinstance(param.name, cst.Name)}
    new_params = list(existing)

    for index, name in enumerate(names):
        if name in existing_names:
            continue
        annotation = annotations[index] if index < len(annotations) else None
        param = cst.Param(name=cst.Name(value=name))
        if annotation is not None:
            param = param.with_changes(annotation=annotation)
        new_params.append(param)

    return params.with_changes(params=new_params)


def _build_new_body(
    statements: Sequence[cst.BaseStatement],
    subtest_loop: _SubtestLoop,
    removable_indexes: Sequence[int],
) -> list[cst.BaseStatement]:
    removable = set(removable_indexes)
    new_body: list[cst.BaseStatement] = []

    for index, stmt in enumerate(statements):
        if index in removable:
            continue
        if index == subtest_loop.index:
            new_body.extend(stmt.deep_clone() for stmt in subtest_loop.body.body)
            continue
        new_body.append(stmt)

    return new_body


def _is_parametrize_decorator(decorator: cst.Decorator) -> bool:
    node = decorator.decorator
    if isinstance(node, cst.Call):
        func = node.func
    else:
        func = node
    if isinstance(func, cst.Attribute) and isinstance(func.attr, cst.Name):
        return func.attr.value == "parametrize"
    if isinstance(func, cst.Name):
        return func.value == "parametrize"
    return False


def _collect_name_values(expr: cst.CSTNode, names: set[str]) -> set[str]:
    found: set[str] = set()

    class _Visitor(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> bool:
            if node.value in names:
                found.add(node.value)
            return True

    expr.visit(_Visitor())
    return found
