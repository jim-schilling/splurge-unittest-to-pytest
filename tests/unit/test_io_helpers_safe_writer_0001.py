from splurge_unittest_to_pytest.io_helpers import safe_file_writer


def test_safe_writer_rejects_windows_system_dir(monkeypatch, tmp_path):
    # Simulate WINDIR pointing to a system dir and attempt to write inside it
    system_dir = tmp_path / "Windows"
    system_dir.mkdir()
    monkeypatch.setenv("WINDIR", str(system_dir))

    target = system_dir / "somefile.ndjson"
    try:
        safe_file_writer(target)
        raised = False
    except ValueError:
        raised = True

    assert raised, "Expected safe_file_writer to reject writing inside WINDIR"


def test_safe_writer_allows_safe_path(tmp_path):
    out_file = tmp_path / "out.ndjson"
    fp = None
    try:
        fp = safe_file_writer(out_file)
        fp.write('{"ok": true}\n')
    finally:
        if fp:
            fp.close()

    # Confirm file exists and is readable
    text = out_file.read_text(encoding="utf-8")
    assert '"ok": true' in text
