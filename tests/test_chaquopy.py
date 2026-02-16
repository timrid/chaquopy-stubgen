from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_cast(mypy_project_dir: Path):
    code = """\
from java import cast
from java.lang import Boolean, Object

b = Boolean(True)
b_Object = cast(Object, b)
reveal_type(b_Object)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.lang.Object"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_jclass(mypy_project_dir: Path):
    code = """\
from java import jclass

Calendar = jclass("java.util.Calendar")
reveal_type(Calendar)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "type[java.lang.Object]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
