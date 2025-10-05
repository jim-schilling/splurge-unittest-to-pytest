import pytest

from splurge_unittest_to_pytest.result import Result, ResultStatus


def test_success_and_to_dict_and_str():
    r = Result.success(123, metadata={"x": 1})
    assert r.is_success()
    assert not r.is_error()
    assert r.unwrap() == 123
    d = r.to_dict()
    assert d["status"] == "success"
    assert d["data"] == 123
    assert "x" in r.metadata
    assert "success" in str(r)


def test_failure_and_unwrap_raises_and_or_else():
    err = RuntimeError("fail")
    r = Result.failure(err, metadata={"f": True})
    assert r.is_error()
    with pytest.raises(RuntimeError):
        r.unwrap()
    assert r.or_else(999) == 999
    assert "error" in str(r)


def test_warning_and_map_and_repr():
    r = Result.warning([1, 2], ["warn1"])
    assert r.is_warning()
    mapped = r.map(lambda lst: [x * 2 for x in lst])
    assert mapped.is_warning()
    assert mapped.data == [2, 4]
    assert "warning" in str(r)
    assert "status=warning" in repr(r)


def test_skipped_and_map_bind_behavior():
    r = Result.skipped("no-op")
    assert r.is_skipped()
    mapped = r.map(lambda x: x)
    assert mapped.is_skipped()
    bound = r.bind(lambda x: Result.success(x))
    assert bound.is_skipped()


def test_map_over_none_data_returns_failure():
    r = Result.success(None)
    res = r.map(lambda x: x)
    assert res.is_error()
    assert isinstance(res.error, Exception)


def test_map_raises_turns_into_failure():
    r = Result.success(5)

    def bad(x):
        raise ValueError("boom")

    res = r.map(bad)
    assert res.is_error()


def test_bind_chaining_and_exception_in_bind():
    r = Result.success(2)

    def to_result(x):
        return Result.success(x * 3)

    chained = r.bind(to_result)
    assert chained.is_success()
    assert chained.unwrap() == 6

    def bad_bind(x):
        raise RuntimeError("bind-err")

    res2 = r.bind(bad_bind)
    assert res2.is_error()


def test_consistency_checks_in_post_init():
    # Direct construction that violates invariants should raise
    with pytest.raises(ValueError):
        Result(status=ResultStatus.SUCCESS, error=RuntimeError("x"))


def test_or_else_and_unwrap_or_paths():
    r = Result.success(10)
    assert r.or_else(99) == 10
    assert r.unwrap_or(99) == 10

    r2 = Result.failure(RuntimeError("fail"))
    assert r2.or_else(7) == 7
    assert r2.unwrap_or(7) == 7


def test_map_and_bind_on_error_and_skipped():
    err = Result.failure(RuntimeError("boom"))
    mapped = err.map(lambda x: x)
    assert mapped.is_error()

    sk = Result.skipped("skip")
    assert sk.map(lambda x: x).is_skipped()
    assert sk.bind(lambda x: Result.success(x)).is_skipped()
