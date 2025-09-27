"""Skip/skipIf decorator rewrites extracted from the main transformer."""

from __future__ import annotations

import libcst as cst


def rewrite_skip_decorators(decorators: list[cst.Decorator] | None) -> list[cst.Decorator] | None:
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
            # Otherwise keep as-is
            new_decorators.append(d)
        except Exception:
            new_decorators.append(d)

    return new_decorators if changed else decorators
