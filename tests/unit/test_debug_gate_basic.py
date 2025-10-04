"""Unit test for transformers.debug maybe_reraise behavior."""

from __future__ import annotations

import os

import pytest

from splurge_unittest_to_pytest.transformers import debug


def test_maybe_reraise_no_debug():
    # Ensure not set
    os.environ.pop("SPLURGE_TRANSFORM_DEBUG", None)
    # Should not raise
    debug.maybe_reraise(ValueError("no debug"))


def test_maybe_reraise_with_debug():
    os.environ["SPLURGE_TRANSFORM_DEBUG"] = "1"
    with pytest.raises(ValueError):
        debug.maybe_reraise(ValueError("debug"))
    os.environ.pop("SPLURGE_TRANSFORM_DEBUG", None)
