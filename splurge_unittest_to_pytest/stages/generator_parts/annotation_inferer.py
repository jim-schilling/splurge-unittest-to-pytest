class AnnotationInferer:
    """Simple annotation inferer used during scaffolding.

    Real implementation will inspect libcst nodes; scaffold exposes a
    predictable interface for unit testing.
    """

    def infer_return_annotation(self, func_name: str) -> str:
        # Trivial heuristic: tests can assert this behavior.
        return "-> Any" if func_name.startswith("test_") else "-> None"
