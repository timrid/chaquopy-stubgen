from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_type_conversions_byte_from_int(mypy_project_dir: Path):
    code = """\
from java.lang import Byte
Byte(5)
"""

    expected_mypy_output = {}

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_type_conversions_byte_from_string(mypy_project_dir: Path):
    code = """\
from java.lang import Byte
Byte("Testing")
"""

    expected_mypy_output = {}

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
