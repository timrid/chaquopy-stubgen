from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_bitarray_stub_is_valid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
"""

    expected_mypy_output = {}

    run_and_assert_mypy(mypy_project_dir, stub_dir, code, expected_mypy_output)


def test_mangled_methods_are_generated(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).and_(BitSet(2))
BitSet(1).or_(BitSet(2))
"""

    expected_mypy_output = {}

    run_and_assert_mypy(mypy_project_dir, stub_dir, code, expected_mypy_output)


def test_no_unmangled_methods_are_generated_and(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).and(BitSet(2))
"""

    expected_mypy_output = """\
testfile.py:2: error: Invalid syntax  [syntax]
Found 1 error in 1 file (errors prevented further checking)
"""

    run_and_assert_mypy(mypy_project_dir, stub_dir, code, expected_mypy_output)


def test_no_unmangled_methods_are_generated_or(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).or(BitSet(2))
"""

    expected_mypy_output = """\
testfile.py:2: error: Invalid syntax  [syntax]
Found 1 error in 1 file (errors prevented further checking)
"""

    run_and_assert_mypy(mypy_project_dir, stub_dir, code, expected_mypy_output)
