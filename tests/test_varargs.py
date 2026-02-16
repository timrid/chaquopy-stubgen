from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_varargs_ints(mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList(5, 23, 42)
reveal_type(java_list)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.List[builtins.int]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_varargs_strings(mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList('test', 'foo')
reveal_type(java_list)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.List[builtins.str]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_varargs_mixed(mypy_project_dir: Path):
    code = """\
from java.util import Arrays

java_list = Arrays.asList('life', 'universe', 'everything', 42)
reveal_type(java_list)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.List[builtins.object]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
