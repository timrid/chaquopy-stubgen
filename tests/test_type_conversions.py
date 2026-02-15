from .conftest import run_mypy
from pathlib import Path


def test_type_conversions_byte_from_int(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import Byte
Byte(5)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
Success: no issues found in 1 source file
""",
    )


def test_type_conversions_byte_from_string(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import Byte
Byte("Testing")
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
Success: no issues found in 1 source file
""",
    )


