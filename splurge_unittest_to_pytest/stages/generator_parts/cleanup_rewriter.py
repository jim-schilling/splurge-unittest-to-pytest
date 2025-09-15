DOMAINS = ["generator", "rewriter"]

# Associated domains for this module


class CleanupRewriter:
    """Scaffold cleanup rewriter that returns a normalized cleanup string."""

    def rewrite(self, cleanup_code: str) -> str:
        # trivial normalization for tests
        return cleanup_code.strip()
