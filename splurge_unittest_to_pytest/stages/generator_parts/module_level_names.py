from __future__ import annotations

from typing import Any, Set

import libcst as cst

DOMAINS = ["generator", "naming"]


# Associated domains for this module


def collect_module_level_names(module_obj: Any) -> Set[str]:
    """Collect top-level names defined in a libcst Module.

    Names are gathered from assignments, function/class defs, and import
    targets. Returns an empty set for non-Module inputs.
    """
    names: Set[str] = set()
    module = module_obj if isinstance(module_obj, cst.Module) else None
    if module is None:
        return names

    for node in module.body:
        # assignments
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, cst.Assign):
                    for t in getattr(stmt, "targets", []):
                        target = getattr(t, "target", t)
                        if isinstance(target, cst.Name):
                            names.add(target.value)
        # def/class names
        if isinstance(node, cst.FunctionDef):
            names.add(node.name.value)
        if isinstance(node, cst.ClassDef):
            names.add(node.name.value)
        # imports - be defensive about ImportStar and name kinds
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, cst.Import):
                    for alias in getattr(stmt, "names") or []:
                        asname = getattr(alias, "asname", None)
                        if asname and isinstance(getattr(asname, "name", None), cst.Name):
                            names.add(asname.name.value)
                        else:
                            base = None
                            nname = getattr(alias, "name", None)
                            if isinstance(nname, str):
                                base = nname.split(".")[0]
                            else:
                                val = getattr(nname, "value", None)
                                if isinstance(val, str):
                                    base = val.split(".")[0]
                            if base:
                                names.add(base)
                if isinstance(stmt, cst.ImportFrom):
                    import_names = getattr(stmt, "names", None)
                    if import_names and isinstance(import_names, (list, tuple)):
                        for alias in import_names:
                            asname = getattr(alias, "asname", None)
                            if asname and isinstance(getattr(asname, "name", None), cst.Name):
                                names.add(asname.name.value)
                            else:
                                nname = getattr(alias, "name", None)
                                base = None
                                if isinstance(nname, str):
                                    base = nname
                                else:
                                    val = getattr(nname, "value", None)
                                    if isinstance(val, str):
                                        base = val
                                if base:
                                    names.add(base)

    return names
