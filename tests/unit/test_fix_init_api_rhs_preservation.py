import pathlib
from splurge_unittest_to_pytest import main


def test_init_api_rhs_preserved():
    # Read the original unittest source saved as text
    src = pathlib.Path(__file__).parent.parent / "data" / "test_init_api.py.txt"
    src_text = src.read_text(encoding="utf8")
    result = main.convert_string(src_text)
    out = result.converted_code if hasattr(result, "converted_code") else str(result)

    # Check that the generated composite fixture yields string-coerced values
    assert "yield _InitAPIData(str(sql_file), str(schema_file))" in out

    # Also ensure downstream simple fixtures return those values
    assert "def sql_file(init_api_data):" in out
    assert "return init_api_data.sql_file" in out
    assert "def schema_file(init_api_data):" in out
    assert "return init_api_data.schema_file" in out
