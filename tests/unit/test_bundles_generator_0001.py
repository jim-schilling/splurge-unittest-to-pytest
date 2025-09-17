from splurge_unittest_to_pytest.stages.generator_parts import bundler_invoker
from splurge_unittest_to_pytest.stages.generator_parts.bundler_invoker import safe_bundle_named_locals


def test_safe_bundle_named_locals_no_classes():
    nodes, needs, mapping = bundler_invoker.safe_bundle_named_locals({}, set())
    assert nodes == []
    assert needs == set()
    assert mapping == {}


def test_safe_bundle_named_locals_exception(monkeypatch):
    def fake_bundle(_out, _names):
        raise RuntimeError("boom")

    monkeypatch.setattr(bundler_invoker, "bundle_named_locals", fake_bundle)
    nodes, needs, mapping = bundler_invoker.safe_bundle_named_locals({"C": {}}, {"X"})
    assert nodes == []
    assert needs == set()
    assert mapping == {}


def test_safe_bundle_named_locals_happy_path_empty():
    nodes, typing, mapping = safe_bundle_named_locals({}, set())
    assert nodes == []
    assert typing == set()
    assert mapping == {}


def test_safe_bundle_named_locals_exception_path(monkeypatch):
    import splurge_unittest_to_pytest.stages.generator_parts.namedtuple_bundler as nb

    orig = nb.bundle_named_locals

    def _bad(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(nb, "bundle_named_locals", _bad)
    nodes, typing, mapping = safe_bundle_named_locals({"X": object()}, set())
    assert nodes == []
    assert typing == set()
    assert mapping == {}
    monkeypatch.setattr(nb, "bundle_named_locals", orig)
