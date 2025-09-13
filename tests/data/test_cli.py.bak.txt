import os
import subprocess
import sys
import tempfile
import unittest
import re

from tests.unit.test_utils import create_basic_schema, create_sql_with_schema

SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'splurge_sql_generator', 'cli.py')


def run_cli(args, input_sql=None):
    cmd = [sys.executable, SCRIPT] + args
    if input_sql:
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".sql") as f:
            f.write(input_sql)
            fname = f.name
        args = [fname] + args[1:]
        cmd = [sys.executable, SCRIPT] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if input_sql:
        os.remove(fname)
    return result


def test_cli_help():
    """Test CLI help output."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True,
        text=True,
    )
    assert "usage" in result.stdout.lower()
    assert "Generate Python SQLAlchemy classes" in result.stdout
    assert result.returncode == 0


def test_cli_missing_file():
    """Test CLI with non-existent file."""
    result = run_cli(['not_a_file.sql'])
    assert result.returncode != 0
    assert 'SQL file not found' in result.stderr


def test_cli_wrong_extension(tmp_path):
    """Test CLI with non-SQL file extension."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f:
        f.write("SELECT 1;")
        fname = f.name
    try:
        result = run_cli([fname])
        assert ".sql extension" in result.stderr
    finally:
        os.remove(fname)


def test_cli_dry_run(tmp_path):
    """Test CLI dry-run mode."""
    sql = """# TestClass
#get_foo
SELECT 1;
    """
    sql_file = tmp_path / 'test.sql'
    sql_file.write_text(sql)
    
    # Create schema file
    schema_file = tmp_path / 'test.schema'
    schema_file.write_text(create_basic_schema("dummy"))
    
    result = run_cli([str(sql_file), "--dry-run"])
    assert "class TestClass" in result.stdout
    assert "def get_foo" in result.stdout
    assert result.returncode == 0


def test_cli_non_sql_extension(tmp_path):
    """Test CLI with non-SQL extension but valid SQL content."""
    # Create the .txt file
    file = tmp_path / 'foo.txt'
    file.write_text('# TestClass\n# test_method\nSELECT 1;')
    
    # Create the schema file with .schema extension
    schema_file = tmp_path / 'foo.schema'
    schema_file.write_text(create_basic_schema())

    result = run_cli([str(file)])
    # Should warn but still run
    assert 'Warning' in result.stderr
    assert result.returncode == 0
    # Should report generated file
    assert 'test_class.py' in result.stdout


def test_cli_output_dir(tmp_path):
    """Test CLI with output directory."""
    sql_file = tmp_path / 'bar.sql'
    sql_file.write_text('# TestClass\n# test_method\nSELECT 1;')
    
    # Create schema file
    schema_file = tmp_path / 'bar.schema'
    schema_file.write_text(create_basic_schema())
    
    outdir = tmp_path / 'outdir'
    result = run_cli([str(sql_file), '-o', str(outdir)])
    assert result.returncode == 0
    assert outdir.exists()
    py_file = outdir / 'test_class.py'
    assert py_file.exists()
    assert 'class TestClass' in py_file.read_text()


def test_cli_report_generated_classes(tmp_path):
    """Test CLI reports generated classes correctly."""
    sql_file = tmp_path / 'baz.sql'
    sql_file.write_text('# TestClass\n# test_method\nSELECT 1;')
    
    # Create schema file
    schema_file = tmp_path / 'baz.schema'
    schema_file.write_text(create_basic_schema())
    
    outdir = tmp_path / 'outdir2'
    result = run_cli([str(sql_file), '-o', str(outdir)])
    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)
    assert 'test_class.py' in result.stdout


def test_cli_multiple_files(tmp_path):
    """Test CLI with multiple SQL files."""
    # Create multiple SQL files
    sql_file1 = tmp_path / 'class1.sql'
    sql_file1.write_text('# ClassOne\n#method1\nSELECT 1;')
    schema_file1 = tmp_path / 'class1.schema'
    schema_file1.write_text(create_basic_schema("table1"))
    
    sql_file2 = tmp_path / 'class2.sql'
    sql_file2.write_text('# ClassTwo\n#method2\nSELECT 2;')
    schema_file2 = tmp_path / 'class2.schema'
    schema_file2.write_text(create_basic_schema("table2"))
    
    outdir = tmp_path / 'multi_out'
    result = run_cli([str(sql_file1), str(sql_file2), '-o', str(outdir)])
    
    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)
    assert 'class_one.py' in result.stdout
    assert 'class_two.py' in result.stdout
    
    # Check files were created
    assert (outdir / 'class_one.py').exists()
    assert (outdir / 'class_two.py').exists()


def test_cli_directory_processing(tmp_path):
    """Test CLI with directory containing SQL files."""
    # Create a directory with SQL files
    sql_dir = tmp_path / 'sql_files'
    sql_dir.mkdir()
    
    create_sql_with_schema(sql_dir, 'class1.sql', '# ClassOne\n#method1\nSELECT 1;', create_basic_schema("table1"))
    create_sql_with_schema(sql_dir, 'class2.sql', '# ClassTwo\n#method2\nSELECT 2;', create_basic_schema("table2"))
    
    # Add a non-SQL file to ensure it's ignored
    txt_file = sql_dir / 'readme.txt'
    txt_file.write_text('This is not SQL')
    
    outdir = tmp_path / 'dir_out'
    result = run_cli([str(sql_dir), '-o', str(outdir)])
    
    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)
    assert 'class_one.py' in result.stdout
    assert 'class_two.py' in result.stdout


def test_cli_empty_directory(tmp_path):
    """Test CLI with empty directory."""
    empty_dir = tmp_path / 'empty_dir'
    empty_dir.mkdir()
    
    result = run_cli([str(empty_dir)])
    assert 'No .sql files found' in result.stderr
    assert result.returncode == 0


def test_cli_empty_directory_strict_mode(tmp_path):
    """Test CLI with empty directory in strict mode."""
    empty_dir = tmp_path / 'empty_dir_strict'
    empty_dir.mkdir()
    
    result = run_cli([str(empty_dir), '--strict'])
    assert 'No .sql files found' in result.stderr
    assert result.returncode != 0


def test_cli_invalid_sql_file(tmp_path):
    """Test CLI with invalid SQL file (missing class comment)."""
    create_sql_with_schema(tmp_path, 'invalid.sql', 'SELECT 1;')  # Missing class comment

    result = run_cli([str(tmp_path / 'invalid.sql')])
    assert result.returncode != 0
    assert 'class comment' in result.stderr


def test_cli_invalid_class_name(tmp_path):
    """Test CLI with invalid class name (reserved keyword)."""
    create_sql_with_schema(tmp_path, 'invalid_class.sql', '# class\n#method\nSELECT 1;')  # 'class' is reserved

    result = run_cli([str(tmp_path / 'invalid_class.sql')])
    assert result.returncode != 0
    assert 'reserved keyword' in result.stderr


def test_cli_invalid_method_name(tmp_path):
    """Test CLI with invalid method name (reserved keyword)."""
    create_sql_with_schema(tmp_path, 'invalid_method.sql', '# TestClass\n#def\nSELECT 1;')  # 'def' is reserved

    result = run_cli([str(tmp_path / 'invalid_method.sql')])
    assert result.returncode != 0
    assert 'reserved keyword' in result.stderr


def test_cli_complex_sql_with_parameters(tmp_path):
    """Test CLI with complex SQL containing parameters."""
    create_sql_with_schema(tmp_path, 'complex.sql', """# ComplexClass
#get_user_by_id
SELECT id, username, email 
FROM users 
WHERE id = :user_id AND status = :status;

#create_user
INSERT INTO users (username, email, password_hash) 
VALUES (:username, :email, :password_hash) 
RETURNING id;
""")

    outdir = tmp_path / 'complex_out'
    result = run_cli([str(tmp_path / 'complex.sql'), '-o', str(outdir)])

    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)
    assert 'complex_class.py' in result.stdout

    # Check generated file contains expected content
    py_file = outdir / 'complex_class.py'
    content = py_file.read_text()
    assert 'class ComplexClass:' in content
    assert 'def get_user_by_id(' in content
    assert 'def create_user(' in content
    # Check that parameters have type annotations (may be Any, int, str, etc.)
    assert re.search(r'user_id:\s*[^\s,]+,', content), "user_id parameter with type annotation not found"
    assert re.search(r'status:\s*[^\s,]+,', content), "status parameter with type annotation not found"


def test_cli_dry_run_multiple_files(tmp_path):
    """Test CLI dry-run with multiple files."""
    create_sql_with_schema(tmp_path, 'dry1.sql', '# DryOne\n#method1\nSELECT 1;')
    create_sql_with_schema(tmp_path, 'dry2.sql', '# DryTwo\n#method2\nSELECT 2;')

    result = run_cli([str(tmp_path / 'dry1.sql'), str(tmp_path / 'dry2.sql'), '--dry-run'])

    assert result.returncode == 0
    assert 'Generated class: DryOne' in result.stdout
    assert 'Generated class: DryTwo' in result.stdout
    assert 'class DryOne:' in result.stdout
    assert 'class DryTwo:' in result.stdout


def test_cli_output_dir_creation(tmp_path):
    """Test CLI creates output directory if it doesn't exist."""
    create_sql_with_schema(tmp_path, 'create_dir.sql', '# CreateDir\n#method\nSELECT 1;')

    # Use a nested output directory that doesn't exist
    outdir = tmp_path / 'nested' / 'output' / 'dir'
    result = run_cli([str(tmp_path / 'create_dir.sql'), '-o', str(outdir)])

    assert result.returncode == 0
    assert outdir.exists()
    assert (outdir / 'create_dir.py').exists()


def test_cli_file_permission_error(tmp_path):
    """Test CLI handles file permission errors gracefully."""
    create_sql_with_schema(tmp_path, 'permission.sql', '# Permission\n#method\nSELECT 1;')
    sql_file = tmp_path / 'permission.sql'

    # Make the file read-only
    sql_file.chmod(0o444)

    try:
        result = run_cli([str(sql_file)])
        # Should still work since we're only reading
        assert result.returncode == 0
    finally:
        # Restore permissions
        sql_file.chmod(0o666)





def test_cli_mixed_valid_invalid_files(tmp_path):
    """Test CLI with mix of valid and invalid SQL files."""
    # Valid file
    create_sql_with_schema(tmp_path, 'valid.sql', '# ValidClass\n#method\nSELECT 1;')

    # Invalid file (missing class comment)
    create_sql_with_schema(tmp_path, 'invalid.sql', 'SELECT 1;')

    result = run_cli([str(tmp_path / 'valid.sql'), str(tmp_path / 'invalid.sql')])

    # Should fail due to invalid file
    assert result.returncode != 0
    assert 'class comment' in result.stderr


def test_cli_unicode_content(tmp_path):
    """Test CLI handles Unicode content correctly."""
    create_sql_with_schema(tmp_path, 'unicode.sql', """# UnicodeClass
#get_user_by_name
SELECT id, name 
FROM users 
WHERE name LIKE :name_pattern;
""")

    outdir = tmp_path / 'unicode_out'
    result = run_cli([str(tmp_path / 'unicode.sql'), '-o', str(outdir)])

    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)

    # Check generated file
    py_file = outdir / 'unicode_class.py'
    content = py_file.read_text(encoding='utf-8')
    assert 'class UnicodeClass:' in content
    # Note: Parameters now use specific types based on naming patterns
    assert 'name_pattern: str,' in content


def test_cli_large_sql_file(tmp_path):
    """Test CLI with large SQL file."""
    # Create a large SQL file with many methods
    content = ['# LargeClass']
    for i in range(100):
        content.append(f'#method_{i}')
        content.append(f'SELECT {i} as value;')

    create_sql_with_schema(tmp_path, 'large.sql', '\n'.join(content))

    outdir = tmp_path / 'large_out'
    result = run_cli([str(tmp_path / 'large.sql'), '-o', str(outdir)])

    assert result.returncode == 0
    assert re.search(r'Generated \d+ Python classes?', result.stdout)

    # Check generated file
    py_file = outdir / 'large_class.py'
    content = py_file.read_text()
    assert 'class LargeClass:' in content
    # Should have many methods
    assert content.count('def method_') >= 100


def test_cli_no_arguments():
    """Test CLI with no arguments."""
    result = subprocess.run(
        [sys.executable, SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'arguments are required' in result.stderr


def test_cli_invalid_option():
    """Test CLI with invalid option."""
    result = subprocess.run(
        [sys.executable, SCRIPT, '--invalid-option'],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'unrecognized arguments' in result.stderr


if __name__ == "__main__":
    unittest.main()
