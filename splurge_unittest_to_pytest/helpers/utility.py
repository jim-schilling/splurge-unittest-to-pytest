"""Utility helpers used by transformers and other modules.

This module contains small, focused helpers for balanced parsing of
function-call argument lists, safe string-based replacements of ``self.*``
calls, and simple filename/extension sanitizers. The functions are used
by legacy string-based transformers in the project and are implemented to
be conservative and robust against nested brackets and quoted strings.
"""

from collections.abc import Callable


def emit_indented_str(s: str, indent: int = 0) -> str:
    """Return the input string prefixed with a number of spaces.

    Args:
        s: The string to indent.
        indent: Number of spaces to prefix (negative values are treated as 0).

    Returns:
        The indented string.
    """
    indent = max(0, indent)
    return f"{' ' * indent}{s}"


def split_two_args_balanced(s: str) -> tuple[str, str] | None:
    """Split a string containing two comma-separated arguments while
    respecting nested brackets and quoted strings.

    The function returns a tuple of the left and right argument strings
    (trimmed). If no top-level comma is found (for example when arguments
    themselves contain commas inside brackets or strings), ``None`` is
    returned.

    Args:
        s: Input string containing two arguments (e.g. "a, b").

    Returns:
        ``(left, right)`` when a top-level comma is present, otherwise
        ``None``.
    """
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
    """Safely replace occurrences of ``self.<func_name>(arg1, arg2)`` in code.

    This function performs balanced parsing to locate the call site and
    extracts the inner argument text while respecting nested parentheses,
    brackets, braces, and quoted strings. It then calls ``format_fn`` with
    the two extracted argument strings to produce a replacement string.

    Args:
        code: The source code to search and replace.
        func_name: The method name to look for on ``self`` (without ``self.``).
        format_fn: Callable that accepts ``(arg1, arg2)`` and returns the
            replacement string.

    Returns:
        The transformed source code with replacements applied.
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
    """Safely replace occurrences of ``self.<func_name>(arg)`` in code.

    The parser is conservative and respects nested parentheses/brackets and
    both single and double quoted strings. The extracted inner text is
    passed (trimmed) to ``format_fn`` which should return the replacement
    snippet.

    Args:
        code: Source code to process.
        func_name: Method name to search for on ``self``.
        format_fn: Callable that accepts the inner argument string and
            returns the replacement text.

    Returns:
        The transformed source code.
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
        replacement = format_fn(inner.strip())
        out_parts.append(replacement)
        i = k + 1
    return "".join(out_parts)


def sanitize_suffix(s: str) -> str:
    """Sanitize a user-provided filename suffix.

    The function collapses repeated dots, removes unsafe characters, strips
    leading/trailing dots/underscores/hyphens, and returns an empty string
    when the result is empty. When a non-empty suffix remains it is
    returned with a single leading underscore (``"_suffix"``).

    Args:
        s: User-provided suffix string.

    Returns:
        A sanitized suffix beginning with ``_`` or an empty string when the
        sanitized content is empty.
    """
    import re

    s = re.sub(r"\.{2,}", ".", s)
    s = s.strip(".")
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    s = s.strip("_-")
    return f"_{s}" if s else ""


def sanitize_extension(e: str | None) -> str | None:
    """Sanitize and normalize a file extension string.

    Args:
        e: Extension string supplied by a user (may include leading dot).

    Returns:
        A normalized extension starting with '.' (lower-cased) or ``None``
        if no valid extension can be derived.
    """
    import re

    if e is None:
        return None
    e = e.strip()
    if not e:
        return None
    e = re.sub(r"\.{2,}", "", e)
    e = e.lstrip(".")
    e = re.sub(r"[^A-Za-z0-9]", "", e)
    if not e:
        return None
    return f".{e.lower()}"
