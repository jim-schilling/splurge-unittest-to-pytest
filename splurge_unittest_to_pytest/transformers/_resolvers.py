"""Name-resolution and literal-extraction helpers extracted from parametrize_helper.

These helpers are pure functions operating on sequences of libcst statements
and are safe to unit test in isolation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

import libcst as cst

from ..exceptions import ParametrizeConversionError


class _RemovalCandidate:
    def __init__(self, index: int, name: str | None) -> None:
        self.index = index
        self.name = name


def _extract_literal_elements(node: cst.BaseExpression) -> tuple[cst.BaseExpression, ...] | None:
    if isinstance(node, cst.List | cst.Tuple):
        elements: list[cst.BaseExpression] = []
        for element in node.elements:
            if not isinstance(element, cst.Element):
                return None
            elements.append(element.value)
        return tuple(elements)
    return None


def _extract_dict_pairs(node: cst.BaseExpression) -> tuple[tuple[cst.BaseExpression, cst.BaseExpression], ...] | None:
    if not isinstance(node, cst.Dict):
        return None

    pairs: list[tuple[cst.BaseExpression, cst.BaseExpression]] = []
    for element in node.elements:
        if not isinstance(element, cst.DictElement):
            return None
        pairs.append((element.key, element.value))

    return tuple(pairs)


def _resolve_name_reference(
    name: str,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], int | None] | None:
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
                            mutated = False
                            for midx in range(idx + 1, loop_index):
                                mid_stmt = statements[midx]
                                if isinstance(mid_stmt, cst.SimpleStatementLine):
                                    for mid_small in mid_stmt.body:
                                        if isinstance(mid_small, cst.Expr) and isinstance(mid_small.value, cst.Call):
                                            func = mid_small.value.func
                                            if isinstance(func, cst.Attribute) and isinstance(func.value, cst.Name):
                                                if func.value.value == name and isinstance(func.attr, cst.Name):
                                                    if func.attr.value in {
                                                        "append",
                                                        "extend",
                                                        "insert",
                                                        "pop",
                                                        "clear",
                                                        "remove",
                                                        "appendleft",
                                                    }:
                                                        mutated = True
                                                        break
                                        if isinstance(mid_small, cst.Assign):
                                            for t in mid_small.targets:
                                                if isinstance(t.target, cst.Name) and t.target.value == name:
                                                    mutated = True
                                                    break
                                    if mutated:
                                        break
                                if isinstance(mid_stmt, cst.AugAssign):
                                    target = mid_stmt.target
                                    if isinstance(target, cst.Name) and target.value == name:
                                        mutated = True
                                        break

                            if mutated:
                                return None

                            removable_index: int | None = idx if len(stmt.body) == 1 else None
                            return elements, removable_index
    return None


def _resolve_sequence_argument(
    expr: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[cst.BaseExpression, ...], tuple[_RemovalCandidate, ...]]:
    literal_values = _extract_literal_elements(expr)
    if literal_values is not None:
        return literal_values, ()

    if isinstance(expr, cst.Name):
        resolution = _resolve_name_reference(expr.value, statements, loop_index)
        if resolution is None:
            raise ParametrizeConversionError
        values, removable_index = resolution
        if removable_index is None:
            return values, ()
        return values, (_RemovalCandidate(index=removable_index, name=expr.value),)

    raise ParametrizeConversionError


def _resolve_mapping_argument(
    expr: cst.BaseExpression,
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> tuple[tuple[tuple[cst.BaseExpression, cst.BaseExpression], ...], tuple[_RemovalCandidate, ...]]:
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
            removal: tuple[_RemovalCandidate, ...]
            if len(stmt.body) == 1:
                removal = (_RemovalCandidate(index=idx, name=name),)
            else:
                removal = ()
            return pairs, removal

    raise ParametrizeConversionError


def _collect_constant_assignment_values(
    statements: Sequence[cst.BaseStatement],
    loop_index: int,
) -> dict[str, cst.BaseExpression]:
    constants: dict[str, cst.BaseExpression] = {}

    for index in range(loop_index):
        stmt = statements[index]
        if not isinstance(stmt, cst.SimpleStatementLine):
            continue
        for small_stmt in stmt.body:
            if isinstance(small_stmt, cst.Assign):
                if len(small_stmt.targets) != 1:
                    continue
                target = small_stmt.targets[0].target
                if not isinstance(target, cst.Name):
                    continue
                value_expr = small_stmt.value
                if _expression_is_constant(value_expr):
                    constants[target.value] = value_expr
            elif isinstance(small_stmt, cst.AnnAssign):
                target = small_stmt.target
                if not isinstance(target, cst.Name):
                    continue

                value_node = small_stmt.value
                if value_node is None:
                    continue
                value_expr = value_node
                if _expression_is_constant(value_expr):
                    constants[target.value] = value_expr

    return constants


def _inline_constant_expression(
    expression: cst.BaseExpression,
    constants: Mapping[str, cst.BaseExpression],
) -> cst.BaseExpression:
    class _ConstantInliner(cst.CSTTransformer):
        def __init__(self, mapping: Mapping[str, cst.BaseExpression]) -> None:
            self.mapping = mapping

        def leave_Name(
            self,
            original_node: cst.Name,
            updated_node: cst.Name,
        ) -> cst.BaseExpression:  # noqa: D401 - libcst signature
            replacement = self.mapping.get(original_node.value)
            if replacement is None:
                return updated_node
            return replacement.deep_clone()

    transformer = _ConstantInliner(constants)
    updated = expression.visit(transformer)
    return cast(cst.BaseExpression, updated)


def _expression_is_constant(expression: cst.CSTNode) -> bool:
    if isinstance(expression, cst.Integer | cst.Float | cst.SimpleString):
        return True

    if isinstance(expression, cst.Name):
        return expression.value in {"True", "False", "None"}

    if isinstance(expression, cst.UnaryOperation):
        return _expression_is_constant(expression.expression)

    if isinstance(expression, cst.List | cst.Tuple | cst.Set):
        return all(
            isinstance(element, cst.Element) and _expression_is_constant(element.value)
            for element in expression.elements
        )

    if isinstance(expression, cst.Dict):
        return all(
            isinstance(element, cst.DictElement)
            and element.key is not None
            and _expression_is_constant(element.key)
            and _expression_is_constant(element.value)
            for element in expression.elements
        )

    if isinstance(expression, cst.BinaryOperation):
        return _expression_is_constant(expression.left) and _expression_is_constant(expression.right)

    if isinstance(expression, cst.Attribute):
        return _expression_is_constant(expression.value)

    return False


def _collect_expression_names(expression: cst.CSTNode) -> set[str]:
    ignored = {"True", "False", "None"}
    collected: set[str] = set()

    class _Collector(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802 - libcst naming
            collected.add(node.value)
            return True

    expression.visit(_Collector())

    return collected.difference(ignored)
