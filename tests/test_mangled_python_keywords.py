from .conftest import run_mypy
from pathlib import Path


def test_bitarray_stub_is_valid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
Success: no issues found in 1 source file
""",
    )


def test_mangled_methods_are_generated(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).and_(BitSet(2))
BitSet(1).or_(BitSet(2))
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
Success: no issues found in 1 source file
""",
    )


def test_no_unmangled_methods_are_generated_and(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).and(BitSet(2))
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:2: error: invalid syntax  [syntax]
Found 1 error in 1 file (errors prevented further checking)
""",
        expected_returncode=2,
    )


def test_no_unmangled_methods_are_generated_or(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import BitSet
BitSet(1).or(BitSet(2))
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:2: error: invalid syntax  [syntax]
Found 1 error in 1 file (errors prevented further checking)
""",
        expected_returncode=2,
    )


