DOMAINS = ["generator", "rewriter"]

# Associated domains for this module


class CleanupRewriter:
    """Scaffold cleanup rewriter that returns a normalized cleanup string.

    The current implementation performs minimal normalization suitable for
    unit tests. The real rewriter will perform more sophisticated cleanup
    transformations on the fixture body.
    """

    def rewrite(self, cleanup_code: str) -> str:
        # trivial normalization for tests
        return cleanup_code.strip()
