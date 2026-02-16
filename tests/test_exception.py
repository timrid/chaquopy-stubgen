from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_java_exception(mypy_project_dir: Path):
    code = """\
from java.lang import Exception
java_exception = Exception("Testing")

reveal_type(java_exception)  # *1

raise RuntimeError("42") from java_exception
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.lang.Exception"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_java_exception_is_python_exception(mypy_project_dir: Path):
    code = """\
import builtins
from java.lang import RuntimeException

def f(e: builtins.Exception) -> None: ...
e = RuntimeException("Error message")

f(e)
"""

    expected_mypy_output = {}

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
