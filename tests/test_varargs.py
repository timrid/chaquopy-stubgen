from .conftest import run_mypy
from pathlib import Path


def test_varargs_ints(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList(5, 23, 42)
reveal_type(java_list)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: note: Revealed type is "java.util.List[builtins.int]"
Success: no issues found in 1 source file
""",
    )


def test_varargs_strings(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList('test', 'foo')
reveal_type(java_list)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: note: Revealed type is "java.util.List[builtins.str]"
Success: no issues found in 1 source file
""",
    )


def test_varargs_mixed(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList('life', 'universe', 'everything', 42)
reveal_type(java_list)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: note: Revealed type is "java.util.List[builtins.object]"
Success: no issues found in 1 source file
""",
    )

