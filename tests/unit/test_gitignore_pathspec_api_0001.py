import types

from splurge_unittest_to_pytest.main import find_unittest_files


def _write_repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    (d / ".gitignore").write_text("ignored.py\n")
    good = d / "good.py"
    ignored = d / "ignored.py"
    good.write_text("import unittest\nclass TestGood(unittest.TestCase):\n    pass\n")
    ignored.write_text("import unittest\nclass TestIgnored(unittest.TestCase):\n    pass\n")
    return d, good, ignored


def test_pathspec_with_match_file(monkeypatch, tmp_path):
    d, good, ignored = _write_repo(tmp_path)

    class FakeSpec:
        def match_file(self, relpath):
            # Return True for ignored.py only
            return relpath == "ignored.py"

    def fake_from_lines(pattern_cls, fh):
        return FakeSpec()

    fake_pkg = types.SimpleNamespace(PathSpec=types.SimpleNamespace(from_lines=fake_from_lines))
    fake_patterns = types.SimpleNamespace(GitWildMatchPattern=None)

    sys_mod = __import__("sys").modules
    monkeypatch.setitem(sys_mod, "pathspec", fake_pkg)
    monkeypatch.setitem(sys_mod, "pathspec.patterns", fake_patterns)

    found = find_unittest_files(d, respect_gitignore=True)
    assert any(p.name == "good.py" for p in found)
    assert all(p.name != "ignored.py" for p in found)


def test_pathspec_with_match_files(monkeypatch, tmp_path):
    d, good, ignored = _write_repo(tmp_path)

    class FakeSpec2:
        def match_files(self, iterable):
            # yield ignored.py to indicate match
            for p in iterable:
                if p == "ignored.py":
                    yield p

    def fake_from_lines2(pattern_cls, fh):
        return FakeSpec2()

    fake_pkg = types.SimpleNamespace(PathSpec=types.SimpleNamespace(from_lines=fake_from_lines2))
    fake_patterns = types.SimpleNamespace(GitWildMatchPattern=None)

    sys_mod = __import__("sys").modules
    monkeypatch.setitem(sys_mod, "pathspec", fake_pkg)
    monkeypatch.setitem(sys_mod, "pathspec.patterns", fake_patterns)

    found = find_unittest_files(d, respect_gitignore=True)
    assert any(p.name == "good.py" for p in found)
    assert all(p.name != "ignored.py" for p in found)
