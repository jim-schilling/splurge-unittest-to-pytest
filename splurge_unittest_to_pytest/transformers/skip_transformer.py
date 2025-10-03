"""Rewrite ``unittest`` skip decorators to pytest equivalents.

This module contains a small helper that converts decorators such as
``@unittest.skip(...)`` and ``@unittest.skipIf(...)`` into pytest's
``@pytest.mark.skip(...)`` and ``@pytest.mark.skipif(...)`` forms using
libcst nodes. The transformation is conservative and preserves any
decorators that it does not recognize.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

import libcst as cst


def rewrite_skip_decorators(decorators: list[cst.Decorator] | None) -> list[cst.Decorator] | None:
    """Convert unittest skip and expected failure decorators into pytest mark decorators.

    This function inspects a list of :class:`libcst.Decorator` nodes and
    replaces occurrences of ``@unittest.skip(...)`` with
    ``@pytest.mark.skip(...)``, ``@unittest.skipIf(...)`` with
    ``@pytest.mark.skipif(...)``, and ``@unittest.expectedFailure`` with
    ``@pytest.mark.xfail``. Arguments supplied to the original
    decorator are preserved.

    Args:
        decorators: A list of :class:`libcst.Decorator` nodes (or
            ``None``) to transform.

    Returns:
        A new list of :class:`libcst.Decorator` nodes if any
        transformations were applied, otherwise the original
        ``decorators`` value.
    """
    if not decorators:
        return decorators

    new_decorators: list[cst.Decorator] = []
    changed = False
    for d in decorators:
        try:
            dec = d.decorator
            # Handle both Call and Attribute decorators
            if isinstance(dec, cst.Call) and isinstance(dec.func, cst.Attribute):
                # We expect a Call: unittest.skip(...)
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
                        changed = True
                        continue
                    elif name.value == "skipIf":
                        mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                        new_call = cst.Call(
                            func=cst.Attribute(value=mark_attr, attr=cst.Name(value="skipif")), args=dec.args
                        )
                        new_decorators.append(cst.Decorator(decorator=new_call))
                        changed = True
                        continue
                    elif name.value == "expectedFailure":
                        # Build @pytest.mark.xfail (no args needed for basic expectedFailure)
                        mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                        new_call = cst.Call(func=cst.Attribute(value=mark_attr, attr=cst.Name(value="xfail")))
                        new_decorators.append(cst.Decorator(decorator=new_call))
                        changed = True
                        continue
            elif isinstance(dec, cst.Attribute):
                # Handle simple Attribute decorators like @unittest.expectedFailure
                owner = dec.value
                name = dec.attr
                if isinstance(owner, cst.Name) and owner.value == "unittest" and isinstance(name, cst.Name):
                    if name.value == "expectedFailure":
                        # Build @pytest.mark.xfail (no args needed for basic expectedFailure)
                        mark_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="mark"))
                        new_call = cst.Call(func=cst.Attribute(value=mark_attr, attr=cst.Name(value="xfail")))
                        new_decorators.append(cst.Decorator(decorator=new_call))
                        changed = True
                        continue
            # Otherwise keep as-is
            new_decorators.append(d)
        except (AttributeError, TypeError, IndexError):
            new_decorators.append(d)

    return new_decorators if changed else decorators
