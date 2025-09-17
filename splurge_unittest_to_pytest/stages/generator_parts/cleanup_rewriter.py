DOMAINS = ["generator", "rewriter"]

# Associated domains for this module


class CleanupRewriter:
    """Minimal cleanup rewriter used in tests.

    This scaffolded rewriter performs trivial normalization of cleanup
    code strings. It exists to keep generator tests deterministic; the
    production rewriter will implement more comprehensive transforms.
    """

    def rewrite(self, cleanup_code: str) -> str:
        # trivial normalization for tests
        return cleanup_code.strip()
