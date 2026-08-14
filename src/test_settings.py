"""Regression tests for settings.config()'s default handling.

These pin the fix for the bug where ``config(var, default=X)`` raised (instead of
returning ``X``) for a variable absent from settings.py's defaults dict: the
step-4 fallback passed ``cast=None`` to decouple, which then called
``None(value)``. Every ``pull_*`` module reads ``config("WRDS_USERNAME")`` at
import, so a test that imports one used to fail in CI (which has no credentials).
"""

import pytest

from settings import config

# A variable name guaranteed not set anywhere (env, .env, cli, defaults dict).
UNSET = "ZZ_DEFINITELY_UNSET_TEST_VAR"


def test_default_is_returned_when_var_unset():
    """A supplied default is returned, not raised over (the core bug)."""
    assert config(UNSET, default="fallback") == "fallback"


def test_explicit_none_default_is_returned():
    """default=None is honored and distinguished from 'no default given'."""
    assert config(UNSET, default=None) is None


def test_missing_var_without_default_raises():
    """With no default, an unset variable still errors clearly."""
    with pytest.raises(ValueError, match="is not defined"):
        config(UNSET)


def test_cast_is_applied_to_default():
    """cast is applied to a returned default (never leaks cast=None to decouple)."""
    assert config(UNSET, default="5", cast=int) == 5
