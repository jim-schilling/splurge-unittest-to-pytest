"""Create inlined consolidated test modules from backup fragments.

Behavior:
- Group fragments by base group key (strip 'test_' prefix and trailing numeric suffixes)
- For each group, produce a single module with:
  - one module docstring (from the first fragment that has one)
  - a deduplicated imports block (Import and ImportFrom)
  - all top-level definitions from each fragment (Assign, AnnAssign, FunctionDef, ClassDef, Expr etc.)
- If a top-level name collides, rename it by appending __NN (two-digit) and rewrite references within that fragment to the new name.

Limitations:
- This is a best-effort inliner. Cross-fragment name references may not be rewritten and could break; those groups will fall back to the runtime-loader if inlining fails.

Output:
- Writes modules to tmp/inlined_consolidated/tests preserving relative paths.
"""

from __future__ import annotations

import argparse
import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


ROOT_BACKUP = Path("backups/converted_preview/20250917T210303Z/tests")
OUT_ROOT = Path("tmp/inlined_consolidated/tests")


def group_key_from_name(name: str) -> str:
    # strip 'test_' prefix and trailing underscore+digits parts (e.g., test_foo_0001 -> foo)
    if name.startswith("test_"):
        core = name[5:]
    else:
        core = name
    core = re.sub(r"(_\d+)+$", "", core)
    core = re.sub(r"__+", "_", core)
    return core or name


def collect_fragments(root: Path) -> Dict[Tuple[str, str], List[Path]]:
    groups: Dict[Tuple[str, str], List[Path]] = defaultdict(list)
    for p in root.rglob("test_*.py"):
        rel = p.relative_to(root)
        group = group_key_from_name(p.stem)
        groups[(str(rel.parent), group)].append(p)
    return groups


class Renamer(ast.NodeTransformer):
    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    def visit_Name(self, node: ast.Name):
        if node.id in self.mapping:
            return ast.copy_location(ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        self.generic_visit(node)
        return node


def dedupe_imports(import_nodes: List[ast.stmt]) -> List[ast.stmt]:
    seen = set()
    out: List[ast.stmt] = []
    for node in import_nodes:
        key = ast.unparse(node).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(node)
    return out


def inline_group(frags: List[Path], out_path: Path) -> Tuple[bool, str]:
    # Build module AST
    imports: List[ast.stmt] = []
    body_nodes: List[ast.stmt] = []
    used_names: set = set()
    docstring = None

    for p in frags:
        src = p.read_text(encoding="utf8")
        try:
            mod = ast.parse(src)
        except SyntaxError as exc:
            return False, f"syntax-error {p}: {exc}"

        # capture docstring from first fragment
        if docstring is None:
            ds = ast.get_docstring(mod)
            if ds:
                docstring = ds

        # collect import nodes
        frag_imports = [n for n in mod.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        imports.extend(frag_imports)

        # remaining nodes: we will inline top-level definitions and assignments
        remaining = [
            n
            for n in mod.body
            if not isinstance(n, (ast.Import, ast.ImportFrom, ast.Expr))
            or (isinstance(n, ast.Expr) and not isinstance(n.value, ast.Constant))
        ]
        # But skip module-level docstring Expr if present
        # compute top-level names in this fragment
        frag_names = set()
        for n in remaining:
            if isinstance(n, ast.FunctionDef) or isinstance(n, ast.ClassDef):
                frag_names.add(n.name)
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        frag_names.add(t.id)
            elif isinstance(n, ast.AnnAssign):
                t = n.target
                if isinstance(t, ast.Name):
                    frag_names.add(t.id)

        # build mapping for collisions (track used names)
        mapping: Dict[str, str] = {}
        for name in sorted(frag_names):
            if name.startswith("__"):
                # skip dunder
                continue
            if name in used_names:
                # find next suffix not used
                i = 1
                while f"{name}__{i:02d}" in used_names:
                    i += 1
                new = f"{name}__{i:02d}"
                mapping[name] = new
                used_names.add(new)
            else:
                used_names.add(name)

        # apply renames to fragment AST
        if mapping:
            renamer = Renamer(mapping)
            new_nodes = [renamer.visit(ast.fix_missing_locations(n)) for n in remaining]
        else:
            new_nodes = remaining

        # append nodes to body
        for n in new_nodes:
            # skip module-level docstring Expr nodes
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                continue
            body_nodes.append(n)

    # dedupe imports and ensure __future__ imports appear first after docstring
    import_nodes = [n for n in imports if isinstance(n, (ast.Import, ast.ImportFrom))]
    import_nodes = dedupe_imports(import_nodes)
    future_imports = [n for n in import_nodes if isinstance(n, ast.ImportFrom) and n.module == "__future__"]
    other_imports = [n for n in import_nodes if not (isinstance(n, ast.ImportFrom) and n.module == "__future__")]

    # construct module ast
    module_body: List[ast.stmt] = []
    if docstring:
        module_body.append(ast.Expr(value=ast.Constant(value=docstring)))
    # future imports must come immediately after docstring
    module_body.extend(future_imports)
    module_body.extend(other_imports)
    # append body_nodes
    module_body.extend(body_nodes)

    module = ast.Module(body=module_body, type_ignores=[])

    # write out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        code = ast.unparse(module)
    except Exception as exc:
        return False, f"unparse-failed: {exc}"
    out_path.write_text(code, encoding="utf8")
    return True, "ok"


def main(*, backup: str | None = None, out: str | None = None, fallback_on_failure: bool = False) -> int:
    b = Path(backup) if backup else ROOT_BACKUP
    o = Path(out) if out else OUT_ROOT
    if not b.exists():
        print("Backup root not found:", b)
        return 2
    groups = collect_fragments(b)
    print(f"Found {len(groups)} groups to inline")
    failed = []
    succeeded = []
    for (rel_dir, group), files in sorted(groups.items()):
        out_path = o / rel_dir / f"test_{group}.py"
        ok, msg = inline_group(files, out_path)
        if not ok:
            # collect failure info
            failed.append(((rel_dir, group), files, msg))
            # If configured to fall back, write a loader-style module and continue (legacy behavior)
            if fallback_on_failure:
                loader_src = _make_loader(files)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(loader_src, encoding="utf8")
                print(f"[fallback] wrote loader for {out_path} due to: {msg}")
                continue
            # Otherwise, stop immediately and produce a triage report
            print("Inlining failed for group:", rel_dir, group)
            print("Reason:", msg)
            print("Fragments:")
            for f in files:
                print("  -", f)
            # write a triage file to the output root for inspection
            triage_path = o / "inline_consolidated_failures.txt"
            triage_path.parent.mkdir(parents=True, exist_ok=True)
            with triage_path.open("w", encoding="utf8") as tf:
                tf.write(f"Inlining failed for group: {rel_dir}/{group}\n")
                tf.write(f"Reason: {msg}\n")
                tf.write("Fragments:\n")
                for f in files:
                    tf.write(f"  - {str(f)}\n")
            print(f"Triage written to: {triage_path}")
            return 3
        else:
            succeeded.append(out_path)

    print(
        f"Inlined modules written: {len(succeeded)}; failed and fell back to loader: {0 if not failed else len(failed)}"
    )
    # If any failures occurred but were handled via fallback, print a summary
    if failed and fallback_on_failure:
        print("Failures occurred but loader fallbacks were written for them:")
        for (rel_dir, group), files, msg in failed:
            print(f"  - group: {rel_dir}/{group}  reason: {msg}")
    return 0


def _make_loader(files: List[Path]) -> str:
    parts = [
        "# Fallback loader-style module (inlining failed for this group)",
        "from __future__ import annotations",
        "_ns_store = []",
        "def _load_and_register(path: str):",
        "    ns: dict = {'__name__': '__consolidated__', '__file__': path}",
        "    with open(path, 'r', encoding='utf-8') as _f:",
        "        src = _f.read()",
        "    code = compile(src, path, 'exec')",
        "    exec(code, ns)",
        "    for name, val in list(ns.items()):",
        "        if name.startswith('__'):",
        "            continue",
        "        if name.startswith('test') or (isinstance(val, type) and any(m.startswith('test') for m in dir(val))):",
        "            target = name",
        "            i = 1",
        "            while target in globals():",
        '                target = f"{name}_{i:02d}"',
        "                i += 1",
        "            globals()[target] = val",
        "    _ns_store.append(ns)",
    ]
    for f in files:
        parts.append(f"_load_and_register(r'{str(f).replace('\\', '/')}')")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", help="backup root", default=str(ROOT_BACKUP))
    ap.add_argument("--out", help="output root", default=str(OUT_ROOT))
    ap.add_argument(
        "--fallback-on-failure", help="write loader fallback and continue on inlining failures", action="store_true"
    )
    args = ap.parse_args()
    # call using keywords to preserve the new keyword-only signature
    raise SystemExit(main(backup=args.backup, out=args.out, fallback_on_failure=args.fallback_on_failure))
