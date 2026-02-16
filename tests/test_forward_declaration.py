from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_argument_type_declaration(mypy_project_dir: Path):
    code = """\
import typing

if typing.TYPE_CHECKING:
    import java.util

def foo(arg: "java.util.Formatter"):
    reveal_type(arg)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.Formatter"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
