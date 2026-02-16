from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_java_exception(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import Exception
java_exception = Exception("Testing")

reveal_type(java_exception)  # *1

raise RuntimeError("42") from java_exception
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.lang.Exception"',
    }

    run_and_assert_mypy(mypy_project_dir, stub_dir, code, expected_mypy_output)
