import textwrap
import libcst as cst

from splurge_unittest_to_pytest.stages import steps_import_injector


def _merge(src: str, existing_idx: int = 0, add_names: set[str] | None = None) -> str:
    mod = cst.parse_module(textwrap.dedent(src))
    merged = steps_import_injector._merge_typing_into_existing(mod, existing_idx, set(add_names or []))
    return merged.code


def test_alias_as_and_comment_preserved():
    src = """
from typing import Optional as Opt  # opt-comment
from typing import List as L  # list-comment

def f(x: Opt[int]) -> L[int]:
    pass
"""
    out = _merge(src)
    assert "# opt-comment" in out
    assert "# list-comment" in out


def test_top_level_definition_blocks_typing_insert():
    # User defines 'List' at top-level; we should not add typing.List for it
    src = """
List = list

def f(x: List[int]):
    pass
"""
    mod = cst.parse_module(textwrap.dedent(src))
    # Ask to add 'List' (simulating detection) but since it's defined top-level, merge shouldn't add
    merged = steps_import_injector._merge_typing_into_existing(mod, 0, set(["List"]))
    assert "from typing import List" not in merged.code


def test_pathlib_detection_skips_typing_path():
    src = """
from pathlib import Path  # already present

def p() -> Path:
    pass
"""
    mod = cst.parse_module(textwrap.dedent(src))
    merged = steps_import_injector._merge_typing_into_existing(mod, 0, set(["Path"]))
    # since pathlib.Path present, typing.Path should not be inserted
    assert "from typing import Path" not in merged.code


def test_duplicate_alias_comments_consolidated():
    src = """
# a
from typing import A  # a-comment
# b
from typing import A  # a-comment

def f(x: A):
    pass
"""
    out = _merge(src)
    # a-comment should appear only once in preserved comments
    assert out.count("# a-comment") == 1
