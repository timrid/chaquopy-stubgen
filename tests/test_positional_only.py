"""
Tests that Java method parameters are enforced as positional-only ('/').

Background: Java methods cannot be called with keyword arguments at runtime.
The stub generator therefore inserts '/' after all regular parameters so mypy
catches any keyword-argument usage at type-check time.

A practical consequence of this is that implementing a Java interface via
dynamic_proxy works even when the overriding Python method uses different
parameter names than those in the stub (which are 'arg1', 'arg2', ... when no
debug info is available in the bytecode).  Because the stub parameters are
positional-only, mypy does not enforce name compatibility in overrides.
"""

from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_keyword_argument_rejected(mypy_project_dir: Path):
    """Calling a Java method with a keyword argument must be a mypy error."""
    code = """\
from java.util import ArrayList

lst: ArrayList[str] = ArrayList()
lst.get(0)          # positional is fine
lst.get(arg1=0)     # *1
"""
    expected_mypy_output = {
        "*1": 'error: Unexpected keyword argument "arg1" for "get" of "ArrayList"',
    }
    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_dynamic_proxy_different_param_names(mypy_project_dir: Path):
    """
    Implementing a Java interface with parameter names that differ from the
    stub must NOT be a mypy error.

    android.jar contains no debug info, so stub parameters are named arg1,
    arg2, ... .  When a user subclasses an interface (e.g. via dynamic_proxy)
    and writes 'def compare(self, first, second)' instead of
    'def compare(self, arg1, arg2)', mypy must accept that because the parent's
    parameters are positional-only.
    """
    code = """\
import typing
from java.util import Comparator

class StringComparator(Comparator[str]):
    def compare(self, first: str, second: str) -> int:  # 'first'/'second' instead of 'arg1'/'arg2'
        if first < second:
            return -1
        if first > second:
            return 1
        return 0
"""
    expected_mypy_output = {}
    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
