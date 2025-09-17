"""Convert TestCase setup/teardown into top-level pytest functions.

This stage consumes the :class:`CollectorOutput` produced by the
collector stage and emits top-level pytest functions derived from recorded
setup assignments. A provided ``pattern_config`` may customize which
method names are treated as setup/teardown.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, cast

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from splurge_unittest_to_pytest.converter.method_params import (
    is_classmethod,
    is_staticmethod,
    first_param_name,
)

DOMAINS = ["stages", "fixtures"]


# Associated domains for this module


# NOTE: helper to decide removal of first param was removed; the current
# staged pipeline keeps instance/class first params to make converted modules
# runnable by default and uses an autouse attach fixture for pytest runs.


def _update_test_function(fn: cst.FunctionDef, fixture_names: Sequence[str], remove_first: bool) -> cst.FunctionDef:
    """Update a test method's parameters for pytest conversion.

    Args:
        fn: The original :class:`libcst.FunctionDef` representing the method.
        fixture_names: Sequence of fixture parameter names to append when the
            first parameter is removed.
        remove_first: When ``True`` drop the original first parameter
            (``self``/``cls``) and append the fixture parameters. When
            ``False`` retain the first parameter for runnability.

    Returns:
        A new :class:`libcst.FunctionDef` with updated parameters.
    """
    params = list(fn.params.params)
    # detect staticmethod/classmethod decorators using consolidated helpers
    if not is_staticmethod(fn):
        if remove_first:
            # drop first param if it's self/cls
            if params:
                fname = first_param_name(fn)
                if fname in ("self", "cls"):
                    params = params[1:]
        else:
            desired_first = cst.Name("cls") if is_classmethod(fn) else cst.Name("self")
            f_name = first_param_name(fn)
            if f_name not in ("self", "cls"):
                # insert desired first param
                params.insert(0, cst.Param(name=desired_first))

    # Append fixture parameters only when we've removed the first param
    # (i.e., converting TestCase methods into plain pytest functions). If
    # we keep the method runnable (retain self/cls), do not append fixture
    # params and rely on the autouse attach fixture to set instance attrs.
    if remove_first:
        for fname in fixture_names:
            params.append(cst.Param(name=cst.Name(fname)))

    new_params = fn.params.with_changes(params=params)
    return fn.with_changes(params=new_params)


def fixtures_stage(context: dict[str, Any]) -> dict[str, Any]:
    module: Optional[cst.Module] = context.get("module")
    collector: Optional[CollectorOutput] = context.get("collector_output")
    # fixture_specs and compat may be provided by earlier stages; they are
    # not needed in this stage's current implementation but may be present
    # in the context. We intentionally do not use them here to keep this
    # stage focused on producing runnable classes and top-level wrappers.

    if module is None or collector is None:
        return {"module": module}

    # Allow configurable setup/teardown name lists via a PatternConfigurator
    # provided in the pipeline context under the 'pattern_config' key.
    pattern_config: Optional[Any] = context.get("pattern_config")

    def _is_setup_name(name: str) -> bool:
        # If a PatternConfigurator is provided, use its normalized matching
        # helpers; otherwise fall back to common defaults.
        try:
            if pattern_config is not None:
                return bool(getattr(pattern_config, "_is_setup_method", lambda n: False)(name))
        except Exception:
            pass
        return name in ("setUp", "setUpClass")

    def _is_teardown_name(name: str) -> bool:
        try:
            if pattern_config is not None:
                return bool(getattr(pattern_config, "_is_teardown_method", lambda n: False)(name))
        except Exception:
            pass
        return name in ("tearDown", "tearDownClass")

    # module body may contain BaseStatement elements; some class members
    # and injected lines are BaseSmallStatement variants. Use a list that
    # accepts either to avoid append type errors when inserting existing
    # nodes from the original tree.
    new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
    classes = collector.classes

    # The project has removed compatibility mode. This stage now always
    # operates in strict pytest mode: drop unittest.TestCase classes, remove
    # setUp/tearDown methods, and emit top-level pytest functions that
    # accept fixture parameters. Autouse attach fixtures are no longer
    # produced.
    strict_pytest_mode = True

    for stmt in module.body:
        if isinstance(stmt, cst.ClassDef) and stmt.name.value in classes:
            cls_info = classes[stmt.name.value]
            new_class_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
            # per-class fixture names come from setup_assignments keys (stable order)
            fixture_names = list(cls_info.setup_assignments.keys())

            for member in stmt.body.body:
                # preserve non-function members (assign, pass, etc.)
                if not isinstance(member, cst.FunctionDef):
                    new_class_body.append(member)
                    continue

                mname = member.name.value
                # handle exact setup/teardown functions
                if _is_setup_name(mname) or _is_teardown_name(mname):
                    # In strict mode, drop setUp/tearDown entirely
                    if strict_pytest_mode:
                        continue
                    else:
                        # Preserve in compat mode for back-compat runnability
                        new_class_body.append(member)
                        continue

                # update test functions discovered by collector or named with test* prefix
                if mname.startswith("test") or member in cls_info.test_methods:
                    # Decide per-class whether to remove the first param by checking
                    # if the class originally inherited from unittest.TestCase.
                    # The collector stores the original ClassDef node which we
                    # consult to detect unittest.TestCase inheritance.
                    cls_info_local = classes.get(stmt.name.value)
                    if cls_info_local is None:
                        # fallback to previously recorded class info if missing
                        cls_info_local = cast(Any, collector.classes.get(stmt.name.value))

                    def _class_inherits_unittest_testcase_from_original(class_info: Any) -> bool:
                        # Use the original node saved in the collector to detect
                        # unittest.TestCase inheritance.
                        node = getattr(class_info, "node", None)
                        if node is None:
                            return False
                        for base in getattr(node, "bases", []) or []:
                            bval = getattr(base, "value", base)
                            if isinstance(bval, cst.Attribute):
                                if (
                                    isinstance(bval.value, cst.Name)
                                    and bval.value.value == "unittest"
                                    and getattr(bval.attr, "value", "") == "TestCase"
                                ):
                                    return True
                            if isinstance(bval, cst.Name) and bval.value == "TestCase":
                                return True
                        return False

                    # Keep the original first parameter (self/cls) so the
                    # converted module remains runnable by default. The
                    # autouse attach fixture will ensure pytest runs still
                    # receive fixture values via request.getfixturevalue.
                    # In strict mode, convert to plain functions (remove first param and add fixtures)
                    updated_fn = _update_test_function(member, fixture_names, remove_first=strict_pytest_mode)
                    # Ensure one blank line between methods inside the class
                    if new_class_body:
                        last = new_class_body[-1]
                        # If the last appended element is not an EmptyLine, insert one
                        if not isinstance(last, cst.EmptyLine):
                            new_class_body.append(cast(cst.BaseSmallStatement | cst.BaseStatement, cst.EmptyLine()))
                    # Retain updated method only in compat mode; in strict mode we will
                    # drop the class and rely on top-level functions.
                    if not strict_pytest_mode:
                        new_class_body.append(updated_fn)
                    continue

                # otherwise retain the member unchanged
                # ensure spacing between methods/defs inside the class
                if new_class_body and isinstance(member, cst.FunctionDef):
                    last = new_class_body[-1]
                    if not isinstance(last, cst.EmptyLine):
                        new_class_body.append(cast(cst.BaseSmallStatement | cst.BaseStatement, cst.EmptyLine()))
                new_class_body.append(member)

            # Emit class only in compat mode; strict mode drops the class entirely
            if not strict_pytest_mode:
                new_class = stmt.with_changes(body=stmt.body.with_changes(body=new_class_body))
                new_body.append(new_class)
            # Create top-level pytest functions for each test method when the
            # class originally inherited from unittest.TestCase. These functions
            # accept fixture parameters and contain a rewritten body where
            # `self.<attr>` is replaced by the fixture name so pytest can inject
            # fixtures directly. The original class and methods are retained so
            # the module remains runnable by calling instance methods.
            cls_original = cls_info

            def _class_inherits_unittest_testcase_from_original(class_info: Any) -> bool:
                node = getattr(class_info, "node", None)
                if node is None:
                    return False
                for base in getattr(node, "bases", []) or []:
                    bval = getattr(base, "value", base)
                    if isinstance(bval, cst.Attribute):
                        if (
                            isinstance(bval.value, cst.Name)
                            and bval.value.value == "unittest"
                            and getattr(bval.attr, "value", "") == "TestCase"
                        ):
                            return True
                    if isinstance(bval, cst.Name) and bval.value == "TestCase":
                        return True
                return False

            # In strict mode we always emit top-level pytest functions for
            # each test method and do not retain the original unittest class.
            if _class_inherits_unittest_testcase_from_original(cls_original):
                for member in stmt.body.body:
                    if not isinstance(member, cst.FunctionDef):
                        continue
                    mname = member.name.value
                    if not (mname.startswith("test") or member in cls_info.test_methods):
                        continue

                    # rewrite `self.attr` -> `attr` in the member body for the
                    # top-level function variant
                    class _SelfAttrRewriter(cst.CSTTransformer):
                        def leave_Attribute(
                            self, original: cst.Attribute, updated: cst.Attribute
                        ) -> cst.BaseExpression:
                            if (
                                isinstance(original.value, cst.Name)
                                and original.value.value == "self"
                                and isinstance(original.attr, cst.Name)
                            ):
                                return cst.Name(original.attr.value)
                            return updated

                    new_body_block = member.body.visit(_SelfAttrRewriter())

                    # build function params from fixture_names (strict mode)
                    params_list = [cst.Param(name=cst.Name(fname)) for fname in fixture_names]
                    params = cst.Parameters(params=params_list)

                    # create top-level test function using the rewritten body
                    top_fn = cst.FunctionDef(
                        name=cst.Name(mname), params=params, body=cast(cst.BaseSuite, new_body_block), decorators=[]
                    )
                    new_body.append(top_fn)
        else:
            new_body.append(stmt)

    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
