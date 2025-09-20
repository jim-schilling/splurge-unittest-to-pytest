import textwrap
import libcst as cst

from splurge_unittest_to_pytest.stages import steps_import_injector


def _merge(src: str, existing_idx: int = 0, add_names: set[str] | None = None) -> str:
    mod = cst.parse_module(textwrap.dedent(src))
    merged = steps_import_injector._merge_typing_into_existing(mod, existing_idx, set(add_names or []))
    return merged.code


def test_alias_inline_comment_preserved():
    src = """
# header
from typing import Optional  # top-comment
from typing import List  # alias-list-comment

def f(x: Optional[int]) -> List[int]:
    pass
"""
    out = _merge(src)
    assert "# top-comment" in out
    assert "# alias-list-comment" in out


def test_trailing_whitespace_comment_preserved():
    src = """
# header
from typing import Optional  # top-comment
from typing import (
    List,  # list-comment
)  # end-parens

def f(x: Optional[int]) -> List[int]:
    pass
"""
    out = _merge(src)
    # ensure both the alias inline comment and the end-parens trailing comment are present
    assert "# list-comment" in out
    assert "# end-parens" in out


def test_varied_ordering_preserves_comments():
    src = """
# before
from typing import (
    List,  # list-comment
)
from typing import Optional  # optional-comment

def f(x: Optional[int]) -> List[int]:
    pass
"""
    out = _merge(src, existing_idx=0)
    assert "# list-comment" in out
    assert "# optional-comment" in out
