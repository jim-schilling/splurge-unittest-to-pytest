"""Regression test: ensure conversion emits fixtures that return absolute paths for created temp files.

This test runs the generator's `convert_string` on the UNITTEST sample from
the docs and asserts the converted pytest source contains fixtures that
construct file paths under `temp_dir` (i.e., they don't just return bare
filenames like 'test.sql').
"""
import re

from splurge_unittest_to_pytest import convert_string


UNITTEST_SRC = r'''
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from splurge_sql_generator import generate_class, generate_multiple_classes
from tests.unit.test_utils import create_sql_with_schema

class TestInitAPI(unittest.TestCase):
    def setUp(self):
        # Create temporary directory for this test
        self.temp_dir = tempfile.mkdtemp()
        self.sql_content = """# TestClass\n# test_method\nSELECT 1;"""
        
        # Use the shared helper function
        sql_file, schema_file = create_sql_with_schema(
            Path(self.temp_dir), 
            "test.sql", 
            self.sql_content
        )
        self.sql_file = str(sql_file)
        self.schema_file = str(schema_file)

    def tearDown(self):
        # Clean up the entire temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_class(self):
        code = generate_class(self.sql_file, schema_file_path=self.schema_file)
        self.assertIn('class TestClass', code)

    def test_generate_multiple_classes(self):
        self.output_dir = self.sql_file + '_outdir'
        os.mkdir(self.output_dir)
        result = generate_multiple_classes([self.sql_file], output_dir=self.output_dir, schema_file_path=self.schema_file)
        self.assertIn('TestClass', result)

'''


def test_converted_fixtures_return_paths():
    converted = convert_string(UNITTEST_SRC)
    output = converted.converted_code

    # Look for a fixture named sql_file that returns a Path(temp_dir) / 'test.sql' or writes to that path
    # Accept some spacing differences but assert we don't see a bare return of 'test.sql' as the fixture implementation.
    assert "def sql_file(" in output or "def sql_file(" in output

    # Fail if fixture body literally returns a bare 'test.sql' string
    bare_return_re = re.compile(r"return\s+['\"]test\.sql['\"]")
    assert not bare_return_re.search(output), "Converted fixture 'sql_file' should not return bare 'test.sql'"

    # Accept either a Path(temp_dir)/'test.sql' construction or a write_text followed by return of str(path)
    path_expr_ok = any(
        token in output
        for token in ["Path(temp_dir) / 'test.sql'", 'Path(temp_dir) / "test.sql"', "path.write_text(sql_content)"]
    )
    # Also accept preserving the original helper call (create_sql_with_schema)
    if not path_expr_ok:
        assert "create_sql_with_schema(" in output, (
            "Converted output should create/write the test file under temp_dir and return its path, "
            "or preserve the helper call that produces it"
        )
