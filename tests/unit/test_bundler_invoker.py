
from splurge_unittest_to_pytest.stages.generator_parts.bundler_invoker import safe_bundle_named_locals


def test_safe_bundle_named_locals_happy_path_empty():
    # empty classes should return empty results
    nodes, typing = safe_bundle_named_locals({}, set())
    assert nodes == []
    assert typing == set()


def test_safe_bundle_named_locals_exception_path(monkeypatch):
    # monkeypatch the underlying bundler to raise
    import splurge_unittest_to_pytest.stages.generator_parts.namedtuple_bundler as nb

    orig = nb.bundle_named_locals

    def _bad(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(nb, "bundle_named_locals", _bad)
    nodes, typing = safe_bundle_named_locals({"X": object()}, set())
    assert nodes == []
    assert typing == set()
    monkeypatch.setattr(nb, "bundle_named_locals", orig)
