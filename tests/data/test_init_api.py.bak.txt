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
        # Test output file
        self.output_file = self.sql_file + '.py'
        generate_class(self.sql_file, output_file_path=self.output_file, schema_file_path=self.schema_file)
        self.assertTrue(os.path.exists(self.output_file))
        with open(self.output_file) as f:
            self.assertIn('class TestClass', f.read())

    def test_generate_multiple_classes(self):
        self.output_dir = self.sql_file + '_outdir'
        os.mkdir(self.output_dir)
        result = generate_multiple_classes([self.sql_file], output_dir=self.output_dir, schema_file_path=self.schema_file)
        self.assertIn('TestClass', result)
        out_file = os.path.join(self.output_dir, 'test_class.py')
        self.assertTrue(os.path.exists(out_file))
        with open(out_file) as f:
            self.assertIn('class TestClass', f.read())

if __name__ == '__main__':
    unittest.main() 