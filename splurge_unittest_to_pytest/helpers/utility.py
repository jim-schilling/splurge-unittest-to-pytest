"""Utility helpers extracted from transformers for reuse.

This module provides balanced parsing helpers used when doing
string-based transformations of calls like self.assertEqual(a, b).
"""

from collections.abc import Callable


def split_two_args_balanced(s: str) -> tuple[str, str] | None:
    """Split a string containing two arguments into (arg1, arg2) respecting brackets and quotes."""
    depth_paren = depth_brack = depth_brace = 0
    in_single = in_double = False
    escape = False
    for i, ch in enumerate(s):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_single:
            if ch == "'":
                in_single = False
            continue
        if in_double:
            if ch == '"':
                in_double = False
            continue
        if ch == "'":
            in_single = True
            continue
        if ch == '"':
            in_double = True
            continue
        if ch == "(":
            depth_paren += 1
            continue
        if ch == ")":
            if depth_paren > 0:
                depth_paren -= 1
            continue
        if ch == "[":
            depth_brack += 1
            continue
        if ch == "]":
            if depth_brack > 0:
                depth_brack -= 1
            continue
        if ch == "{":
            depth_brace += 1
            continue
        if ch == "}":
            if depth_brace > 0:
                depth_brace -= 1
            continue
        if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            left = s[:i].strip()
            right = s[i + 1 :].strip()
            return left, right
    return None


def safe_replace_two_arg_call(code: str, func_name: str, format_fn: Callable[[str, str], str]) -> str:
    """Safely replace calls like self.func_name(arg1, arg2) using balanced parsing.

    format_fn: function taking (arg1: str, arg2: str) -> str replacement
    """
    needle = f"self.{func_name}("
    i = 0
    out_parts: list[str] = []
    while True:
        j = code.find(needle, i)
        if j == -1:
            out_parts.append(code[i:])
            break
        out_parts.append(code[i:j])
        k = j + len(needle)
        depth = 1
        in_single = in_double = False
        escape = False
        while k < len(code):
            ch = code[k]
            if escape:
                escape = False
                k += 1
                continue
            if ch == "\\":
                escape = True
                k += 1
                continue
            if in_single:
                if ch == "'":
                    in_single = False
                k += 1
                continue
            if in_double:
                if ch == '"':
                    in_double = False
                k += 1
                continue
            if ch == "'":
                in_single = True
                k += 1
                continue
            if ch == '"':
                in_double = True
                k += 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth != 0:
            out_parts.append(code[j:k])
            i = k
            continue
        inner = code[j + len(needle) : k]
        split = split_two_args_balanced(inner)
        if not split:
            out_parts.append(code[j : k + 1])
            i = k + 1
            continue
        a1, a2 = split
        replacement = format_fn(a1, a2)
        out_parts.append(replacement)
        i = k + 1
    return "".join(out_parts)


def safe_replace_one_arg_call(code: str, func_name: str, format_fn: Callable[[str], str]) -> str:
    """Safely replace calls like self.func_name(arg) respecting nesting/quotes."""
    needle = f"self.{func_name}("
    i = 0
    out_parts: list[str] = []
    while True:
        j = code.find(needle, i)
        if j == -1:
            out_parts.append(code[i:])
            break
        out_parts.append(code[i:j])
        k = j + len(needle)
        depth = 1
        in_single = in_double = False
        escape = False
        while k < len(code):
            ch = code[k]
            if escape:
                escape = False
                k += 1
                continue
            if ch == "\\":
                escape = True
                k += 1
                continue
            if in_single:
                if ch == "'":
                    in_single = False
                k += 1
                continue
            if in_double:
                if ch == '"':
                    in_double = False
                k += 1
                continue
            if ch == "'":
                in_single = True
                k += 1
                continue
            if ch == '"':
                in_double = True
                k += 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth != 0:
            out_parts.append(code[j:k])
            i = k
            continue
        inner = code[j + len(needle) : k]
        replacement = format_fn(inner.strip())
        out_parts.append(replacement)
        i = k + 1
    return "".join(out_parts)
