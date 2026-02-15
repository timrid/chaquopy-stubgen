from .conftest import run_mypy
from pathlib import Path


def test_java_exception(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import Exception
java_exception = Exception("Testing")

reveal_type(java_exception)

raise RuntimeError("42") from java_exception
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: note: Revealed type is "java.lang.Exception"
Success: no issues found in 1 source file
""",
    )
