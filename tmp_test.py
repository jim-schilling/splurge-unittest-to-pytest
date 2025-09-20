from __future__ import annotations

from typing import Sequence


class cst:
    class Arg:
        pass

    class WithItem:
        pass


def f(a: Sequence[cst.Arg]) -> cst.WithItem:
    return None
