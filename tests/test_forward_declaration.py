
from .conftest import run_mypy
from pathlib import Path


def test_argument_type_declaration(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing

if typing.TYPE_CHECKING:
    import java.util

def foo(arg: "java.util.Formatter"):
    reveal_type(arg)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:7: note: Revealed type is "java.util.Formatter"
Success: no issues found in 1 source file
""",
    )
