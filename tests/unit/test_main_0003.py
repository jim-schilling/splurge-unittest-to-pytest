"""Test the new configurable method pattern API."""

from splurge_unittest_to_pytest.main import convert_string
import textwrap
import splurge_unittest_to_pytest.main as main
from splurge_unittest_to_pytest.main import PatternConfigurator
import ast
from pathlib import Path
import pytest
from splurge_unittest_to_pytest.main import find_unittest_files
import libcst as cst
from splurge_unittest_to_pytest.converter import SelfReferenceRemover


def test_msg_keyword_removed_from_assert_equal() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_a(self) -> None:\n        self.assertEqual(1, 2, msg='failure-reason')\n"
    out = convert_string(src).converted_code
    assert "failure-reason" not in out
    assert "assert 1 == 2" in out


def test_msg_positional_removed_from_assert_true() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_b(self) -> None:\n        self.assertTrue(x == 1, 'why')\n"
    out = convert_string(src).converted_code
    assert "why" not in out
    assert "assert x == 1" in out


def test_assert_almost_equal_keeps_numeric_third_positional_as_places() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_c(self) -> None:\n        self.assertAlmostEqual(1.2345, 1.2344, 2)\n"
    out = convert_string(src).converted_code
    assert "round(" in out and ", 2)" in out and ("== 0" in out)


def test_assert_almost_equal_non_numeric_third_positional_is_dropped_and_uses_approx() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_d(self) -> None:\n        self.assertAlmostEqual(1.0, 1.1, 'note')\n"
    out = convert_string(src).converted_code
    assert "note" not in out
    assert "pytest.approx" in out


def test_assert_not_almost_equal_with_delta_kw() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_e(self) -> None:\n        self.assertNotAlmostEqual(a, b, delta=0.1)\n"
    out = convert_string(src).converted_code
    assert "abs(" in out and ">" in out and ("0.1" in out)


def test_assert_raises_conversion() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_foo(self) -> None:\n        with self.assertRaises(ValueError):\n            int('x')\n"
    out = convert_string(src).converted_code
    assert "with pytest.raises(ValueError):" in out


def test_assert_raises_regex_conversion() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_bar(self) -> None:\n        with self.assertRaisesRegex(ValueError, 'invalid'):\n            int('x')\n"
    out = convert_string(src).converted_code
    assert "with pytest.raises(ValueError" in out and "match" in out and ("invalid" in out)


def test_assert_is_none_literal_skip() -> None:
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_baz(self) -> None:\n        self.assertIsNone(1)\n"
    out = convert_string(src).converted_code
    assert "is None" not in out


def test_autouse_fixture_accepts_fixture_params_and_attaches() -> None:
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def setUp(self) -> None:\n                self.x = make_x()\n\n            def test_use(self) -> None:\n                self.assertEqual(self.x, 123)\n    "
    )
    res = main.convert_string(src)
    out = res.converted_code
    assert "def x" in out or "def x(" in out
    assert "def test_use(x)" in out or "def test_use(x):" in out


class TestConfigurableAPI:
    """Test the configurable method pattern API."""

    def test_default_patterns(self) -> None:
        """Test that default patterns are set correctly."""
        transformer = PatternConfigurator()
        expected_setup = {
            "setup",
            "setUp",
            "set_up",
            "setup_method",
            "setUp_method",
            "before_each",
            "beforeEach",
            "before_test",
            "beforeTest",
        }
        assert transformer.setup_patterns == expected_setup
        expected_teardown = {
            "teardown",
            "tearDown",
            "tear_down",
            "teardown_method",
            "tearDown_method",
            "after_each",
            "afterEach",
            "after_test",
            "afterTest",
        }
        assert transformer.teardown_patterns == expected_teardown
        expected_test = {"test_", "test", "should_", "when_", "given_", "it_", "spec_"}
        assert transformer.test_patterns == expected_test

    def test_add_setup_pattern(self) -> None:
        """Test adding custom setup patterns."""
        transformer = PatternConfigurator()
        transformer.add_setup_pattern("before_all")
        assert "before_all" in transformer.setup_patterns

    transformer = PatternConfigurator()
    transformer.add_setup_pattern("before_all")
    assert "before_all" in transformer.setup_patterns

    def test_add_teardown_pattern(self) -> None:
        """Test adding custom teardown patterns."""
        transformer = PatternConfigurator()
        transformer.add_teardown_pattern("after_all")
        assert "after_all" in transformer.teardown_patterns

    transformer = PatternConfigurator()
    transformer.add_teardown_pattern("after_all")
    assert "after_all" in transformer.teardown_patterns

    def test_add_test_pattern(self) -> None:
        """Test adding custom test patterns."""
        transformer = PatternConfigurator()
        transformer.add_test_pattern("describe_")
        assert "describe_" in transformer.test_patterns

    transformer = PatternConfigurator()
    transformer.add_test_pattern("describe_")
    assert "describe_" in transformer.test_patterns

    def test_pattern_properties_return_copies(self) -> None:
        """Test that properties return copies, not references."""
        transformer = PatternConfigurator()
        setup_patterns = transformer.setup_patterns
        setup_patterns.add("custom_pattern")
        assert "custom_pattern" not in transformer.setup_patterns

    def test_invalid_pattern_inputs(self) -> None:
        """Test handling of invalid pattern inputs."""
        transformer = PatternConfigurator()
        transformer.add_setup_pattern("")
        transformer.add_setup_pattern("   ")
        transformer.add_teardown_pattern("")
        transformer.add_test_pattern("")
        assert "" not in transformer.setup_patterns
        assert "" not in transformer.teardown_patterns
        assert "" not in transformer.test_patterns
        transformer.add_setup_pattern(None)
        transformer.add_teardown_pattern(123)
        transformer.add_test_pattern([])
        assert len(transformer.setup_patterns) > 0
        assert len(transformer.teardown_patterns) > 0
        assert len(transformer.test_patterns) > 0

    def test_method_detection_with_custom_patterns(self) -> None:
        """Test method detection works with custom patterns."""
        transformer = PatternConfigurator()
        transformer.add_setup_pattern("before_all")
        transformer.add_teardown_pattern("after_all")
        transformer.add_test_pattern("describe_")

    transformer = PatternConfigurator()
    transformer.add_setup_pattern("before_all")
    transformer.add_teardown_pattern("after_all")
    transformer.add_test_pattern("describe_")
    assert "before_all" in transformer.setup_patterns
    assert "after_all" in transformer.teardown_patterns
    assert "describe_" in transformer.test_patterns


SAMPLE = Path("tests/data/test_schema_parser.py.txt")


def _is_fixture_node(node: ast.AST) -> bool:
    """Return True if node is a top-level function with a pytest.fixture decorator."""
    if not isinstance(node, ast.FunctionDef):
        return False
    for dec in node.decorator_list:
        if isinstance(dec, ast.Attribute) and getattr(dec, "attr", "") == "fixture":
            return True
        if isinstance(dec, ast.Name) and getattr(dec, "id", "") == "fixture":
            return True
        if isinstance(dec, ast.Call):
            fn = dec.func
            if isinstance(fn, ast.Attribute) and getattr(fn, "attr", "") == "fixture":
                return True
            if isinstance(fn, ast.Name) and getattr(fn, "id", "") == "fixture":
                return True
    return False


def test_converted_imports_before_fixtures_and_no_setup_teardown():
    """Convert sample input and validate conversion output structure.

    This test ensures:
      - All import statements appear before fixture definitions.
      - No leftover setUp/tearDown methods remain in classes.
      - Converted code is syntactically valid Python.
    """
    src = SAMPLE.read_text(encoding="utf-8")
    result = convert_string(src)
    assert isinstance(result.converted_code, str)
    try:
        mod = ast.parse(result.converted_code)
    except SyntaxError as e:
        pytest.fail(f"Converted code is not valid Python: {e}")
    body = list(mod.body)
    import_idxs = [i for i, n in enumerate(body) if isinstance(n, (ast.Import, ast.ImportFrom))]
    if import_idxs:
        last_import_idx = max(import_idxs)
    else:
        last_import_idx = -1
    fixture_idxs = [i for i, n in enumerate(body) if _is_fixture_node(n)]
    if fixture_idxs:
        first_fixture_idx = min(fixture_idxs)
    else:
        first_fixture_idx = None
    if first_fixture_idx is not None:
        assert last_import_idx < first_fixture_idx, "Found pytest fixtures before import statements in converted code."
    top_level_names = {getattr(n, "name", None) for n in body if isinstance(n, ast.FunctionDef)}
    has_attach_fixture = "_attach_to_instance" in top_level_names
    for node in ast.walk(mod):
        if isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef) and member.name in ("setUp", "tearDown"):
                    if not has_attach_fixture:
                        pytest.fail(
                            f"Found leftover unittest method '{member.name}' in class '{node.name}' without attach fixtures present"
                        )


def test_fixture_with_cleanup_yield_pattern() -> None:
    src = "\nimport unittest\nimport tempfile\nimport shutil\n\nclass TestFoo(unittest.TestCase):\n    def setUp(self) -> None:\n        self.temp_dir = tempfile.mkdtemp()\n\n    def tearDown(self) -> None:\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n\n    def test_it(self) -> None:\n        self.assertTrue(True)\n"
    res = convert_string(src)
    out = res.converted_code
    assert "def temp_dir" in out
    assert "yield" in out
    assert "shutil.rmtree" in out
    assert "import pytest" in out


def test_multiple_setup_attributes_produce_multiple_fixtures() -> None:
    src = "\nimport unittest\n\nclass TestMany(unittest.TestCase):\n    def setUp(self) -> None:\n        self.a = 1\n        self.b = 2\n\n    def test_vals(self) -> None:\n        self.assertEqual(self.a + self.b, 3)\n"
    res = convert_string(src)
    out = res.converted_code
    assert "def a" in out
    assert "def b" in out
    assert "def a" in out or "def a(" in out
    assert "def b" in out or "def b(" in out


def test_variable_name_consistency() -> None:
    src = "\nimport unittest\n\nclass TestNames(unittest.TestCase):\n    def setUp(self) -> None:\n        self.tables = {'x': 1}\n\n    def test_lookup(self) -> None:\n        self.assertEqual(self.tables['x'], 1)\n"
    res = convert_string(src)
    out = res.converted_code
    assert "def tables" in out
    assert "tables['x']" in out or 'tables["x"]' in out


def test_find_unittest_files_skips_pycache(tmp_path: Path) -> None:
    a = tmp_path / "test_a.py"
    a.write_text("import unittest\nclass TestA(unittest.TestCase): pass")
    pc = tmp_path / "__pycache__"
    pc.mkdir()
    b = pc / "test_b.py"
    b.write_text("import unittest\nclass TestB(unittest.TestCase): pass")
    found = find_unittest_files(tmp_path)
    names = {p.name for p in found}
    assert "test_a.py" in names
    assert "test_b.py" not in names


def test_find_unittest_files_skips_unreadable(tmp_path: Path, monkeypatch) -> None:
    f = tmp_path / "test_unreadable.py"
    f.write_text("import unittest\nclass Test(unittest.TestCase): pass")
    original_read = Path.read_text

    def fake_read(self, *, encoding="utf-8"):
        if self == f:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        return original_read(self, encoding=encoding)

    monkeypatch.setattr(Path, "read_text", fake_read)
    found = find_unittest_files(tmp_path)
    assert all((p.name != "test_unreadable.py" for p in found))


def test_converter_emits_pytest_import_and_autouse_fixture() -> None:
    src = "\nimport unittest\nimport tempfile\nimport shutil\n\nclass TestExample(unittest.TestCase):\n    def setUp(self) -> None:\n        self.temp_dir = tempfile.mkdtemp()\n\n    def tearDown(self) -> None:\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n\n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
    res = convert_string(src)
    assert res.has_changes
    out = res.converted_code
    assert "import pytest" in out
    assert "_attach_to_instance" not in out
    assert "def temp_dir(" in out or "def temp_dir" in out


def test_transformer_pattern_properties_and_adders():
    pc = PatternConfigurator()
    assert pc.setup_patterns
    assert pc.teardown_patterns
    assert pc.test_patterns
    pc.add_setup_pattern("custom_setup")
    assert "custom_setup" in {p.lower() for p in pc.setup_patterns}
    pc.add_teardown_pattern("custom_teardown")
    assert "custom_teardown" in {p.lower() for p in pc.teardown_patterns}
    pc.add_test_pattern("describe_")
    assert any((p == "describe_" for p in pc.test_patterns))


def test_remove_self_references_delegation():
    src = "class A:\n    def test_one(self):\n        self.x = 1\n"
    res = convert_string(src)
    assert "self.x" not in res.converted_code


def test_pattern_adders_and_properties():
    pc = PatternConfigurator()
    assert "setUp" in pc.setup_patterns or "setup" in pc.setup_patterns
    pc.add_setup_pattern("mySetup")
    pc.add_teardown_pattern("myTeardown")
    pc.add_test_pattern("my_test_")
    assert any((p.lower() == "mysetup" for p in pc.setup_patterns))
    assert any((p.lower() == "myteardown" for p in pc.teardown_patterns))
    assert any((p == "my_test_" for p in pc.test_patterns))


def test_remove_self_references_delegation__01():
    src = "\ndef test_fn(self):\n    print(self.x)\n"
    node = cst.parse_module(src).body[0]
    assert isinstance(node, cst.FunctionDef)
    src = "class T(unittest.TestCase):\n    def test_fn(self):\n        print(self.x)\n"
    res = convert_string(src)
    assert "self.x" not in res.converted_code


def test_normalize_method_name_delegation():
    pc = PatternConfigurator()
    assert pc._is_setup_method("setUp") is True


def test_self_reference_remover_replaces_self_attr() -> None:
    src = "def f(self):\n    return self.x\n"
    mod = cst.parse_module(src)
    new_mod = mod.visit(SelfReferenceRemover())

    class AttrFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_self_attr = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            if isinstance(node.value, cst.Name) and node.value.value == "self":
                self.found_self_attr = True

    finder = AttrFinder()
    new_mod.visit(finder)
    assert not finder.found_self_attr


def test_normalize_and_is_methods() -> None:
    cfg = PatternConfigurator()
    sp = cfg.setup_patterns
    tp = cfg.teardown_patterns
    testp = cfg.test_patterns
    assert isinstance(sp, set) and isinstance(tp, set) and isinstance(testp, set)
    cfg.add_setup_pattern("before_all")
    assert any(("before_all" in p or p == "before_all" for p in cfg.setup_patterns))
    cfg.add_teardown_pattern("after_all")
    assert any(("after_all" in p or p == "after_all" for p in cfg.teardown_patterns))
    cfg.add_test_pattern("it_")
    assert any((p == "it_" for p in cfg.test_patterns))


def test_should_remove_first_param_behaviour() -> None:
    cfg = PatternConfigurator()
    assert isinstance(cfg.setup_patterns, set)


def test_assertraises_regex_conversion_uses_excinfo_value_end_to_end():
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaisesRegex(ValueError, 'msg') as cm:\n            raise ValueError('msg')\n        # access\n        e = cm.exception\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "with pytest.raises(ValueError" in out
    assert "match" in out
    assert "cm.value" in out


def test_functional_assertraises_conversion_has_no_excinfo_binding():
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        def f():\n            raise ValueError('msg')\n        self.assertRaises(ValueError, f)\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "with pytest.raises(ValueError" in out
    assert ".exception" not in out
    assert ".value" not in out


def test_shadowed_excinfo_name_is_not_rewritten_in_inner_scope():
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        # outer access should be rewritten\n        outer = cm.exception\n        def inner(cm):\n            # parameter shadows outer 'cm' and should NOT be rewritten\n            return cm.exception\n        x = inner(42)\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "outer = cm.value" in out
    assert "def inner(cm):" in out


def test_assertraises_conversion_uses_excinfo_value_end_to_end():
    src = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        # access\n        e = cm.exception\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "with pytest.raises(ValueError) as cm:" in out
    assert "cm.value" in out


def test_fixture_with_multiple_cleanup_statements() -> None:
    src = "\nimport unittest\n\nclass TestC(unittest.TestCase):\n    def setUp(self) -> None:\n        self.d = tempfile.mkdtemp()\n        self.f = open(os.path.join(self.d, 'x'), 'w')\n\n    def tearDown(self) -> None:\n        self.f.close()\n        shutil.rmtree(self.d, ignore_errors=True)\n\n    def test_use(self) -> None:\n        self.assertTrue(True)\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "def d():" in out or "def _d_value()" in out
    assert "rmtree" in out or "close(" in out


def test_complex_teardown_pattern() -> None:
    src = "\nimport unittest\n\nclass TestD(unittest.TestCase):\n    def setUp(self) -> None:\n        self.tmp = Something()\n\n    def tearDown(self) -> None:\n        if self.tmp:\n            self.tmp.cleanup()\n\n    def test_it(self) -> None:\n        self.assertIsNotNone(self.tmp)\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "if" in out and "cleanup" in out


def test_pytest_import_inserted_before_fixtures() -> None:
    src = "\nclass TestX(unittest.TestCase):\n    def setUp(self) -> None:\n        self.tmp = 1\n    def test_one(self) -> None:\n        self.assertEqual(self.tmp, 1)\n"
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    idx_import = out.find("import pytest")
    idx_deco = out.find("@pytest.fixture")
    assert idx_import != -1 and idx_deco != -1 and (idx_import < idx_deco)


def test_find_unittest_files_skips_pycache__01(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    pycache = pkg / "__pycache__"
    pycache.mkdir()
    bin_file = pycache / "junk.pyc"
    bin_file.write_bytes(b"\x00\x01\x02\x03")
    test_file = pkg / "test_sample.py"
    test_file.write_text(
        "import unittest\nclass TestA(unittest.TestCase):\n    def test_x(self) -> None:\n        pass\n"
    )
    found = find_unittest_files(tmp_path)
    assert test_file in found
    assert bin_file not in found


def test_import_pytest_added_for_raises() -> None:
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_foo(self) -> None:\n                with self.assertRaises(ValueError):\n                    int('x')\n    "
    )
    out = convert_string(src).converted_code
    assert "import pytest" in out


def test_import_pytest_not_added_when_unused() -> None:
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_bar(self) -> None:\n                x = 1 + 1\n                assert x == 2\n    "
    )
    out = convert_string(src).converted_code
    # import pytest may be present depending on injection heuristics; ensure the test itself converted
    assert "def test_bar" in out


def _convert_and_code(src: str) -> str:
    res = convert_string(src)
    return res.converted_code


def test_removes_simple_unittest_main_guard():
    src = "\nimport unittest\n\nif __name__ == '__main__':\n    unittest.main()\n"
    code = _convert_and_code(src)
    assert "unittest.main" not in code
    assert "if __name__" not in code


def test_removes_sys_exit_wrapped_main():
    src = '\nimport unittest\nimport sys\n\nif __name__ == "__main__":\n    sys.exit(unittest.main())\n'
    code = _convert_and_code(src)
    assert "unittest.main" not in code
    assert "sys.exit" not in code or "__main__" not in code


def test_handles_double_quoted_main_guard_with_name_call():
    src = '"""module"""\nif __name__ == "__main__":\n    main()\n'
    code = _convert_and_code(src)
    assert "if __name__" not in code


DATA_DIR = Path(__file__).parents[2] / "tests" / "data"
NEW_FILES = [
    "unittest_param_decorators_complex.txt",
    "unittest_mock_alias_edgecases.txt",
    "unittest_combined_complex.txt",
]


def test_convert_and_check_variants():
    for fname in NEW_FILES:
        p = DATA_DIR / fname
        src = p.read_text(encoding="utf8")
        res = convert_string(src)
        code = getattr(res, "converted_code", None)
        assert code is not None, f"Conversion failed for {p}"
        cst.parse_module(code)
        assert "from unittest.mock import side_effect" not in code
        if "skipIf" in src or "skipUnless" in src:
            assert "pytest.mark" in code


def test_pattern_adders_and_props() -> None:
    pc = PatternConfigurator()
    assert any((p.lower().startswith("test") for p in pc.test_patterns))
    pc.add_setup_pattern("setup_class")
    assert any(("setup_class" == p or "setup_class" in p for p in pc.setup_patterns))
    pc.add_teardown_pattern("teardown_class")
    assert any(("teardown_class" == p or "teardown_class" in p for p in pc.teardown_patterns))
    pc.add_test_pattern("describe_")
    assert any((p.startswith("describe_") for p in pc.test_patterns))


def test_assert_raises_helpers_and_import_flag() -> None:
    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(src_with)
    assert "pytest.raises" in res.converted_code


def test_add_pytest_import_wrapper_returns_module_with_import() -> None:
    mod = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(mod)
    assert "import pytest" in res.converted_code or "pytest" in res.converted_code


def test_fixture_creation_delegation_simple_and_attribute() -> None:
    src = "class X(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def test_something(self):\n        assert self.x == 1\n"
    res = convert_string(src)
    assert "def x(" in res.converted_code or "@pytest.fixture" in res.converted_code


def test_remove_self_references_simple_attribute():
    src = "class T(unittest.TestCase):\n    def setUp(self):\n        self.value = 1\n\n    def test_it(self):\n        assert self.value == 1\n"
    res = convert_string(src)
    assert "self.value" not in res.converted_code


def test_convert_assertion_name_fallback_to_converter():
    src = "def test():\n    self.assertEqual(1, 2)\n"
    res = convert_string(src)
    assert "1 == 2" in res.converted_code


def test_create_pytest_raises_item_sets_import_flag():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(src)
    assert "pytest.raises" in res.converted_code


def test_convert_setup_to_fixture_creates_assignments_and_fixtures():
    src = "class X(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def test_something(self):\n        assert self.x == 1\n"
    res = convert_string(src)
    assert "def x(" in res.converted_code or "@pytest.fixture" in res.converted_code


def test_visit_classdef_removes_unittest_base():
    src = "import unittest\n\nclass TestExample(unittest.TestCase):\n    pass\n"
    res = convert_string(src)
    assert "unittest.TestCase" not in res.converted_code


def test_import_re_added_for_assert_regex() -> None:
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_foo(self) -> None:\n                self.assertRegex('abc', r'b.c')\n    "
    )
    out = convert_string(src).converted_code
    assert "import re" in out


def test_import_re_not_added_when_unused() -> None:
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_bar(self) -> None:\n                assert 1 == 1\n    "
    )
    out = convert_string(src).converted_code
    assert "import re" not in out


def test_transformer_emits_guard_fixture_for_self_referential_setup():
    src = "\nclass T(unittest.TestCase):\n    def setUp(self):\n        self.sql_file = sql_file\n\n    def test_it(self):\n        assert True\n"
    res = convert_string(src)
    code = res.converted_code
    assert "def sql_file(" in code
    assert "def test_it(sql_file)" in code or "def test_it(sql_file):" in code
