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


def test_varargs_primitive_array(mypy_project_dir: Path):
    """Primitive-array varargs should use the element type, not the array type.

    E.g. IntStream.of(int...) must appear as *values: java.jint, not
    *values: java.chaquopy.JavaArrayJInt.
    """
    code = """\
from java import jint
from java.util.stream import IntStream

s1 = IntStream.of(jint(1), jint(2), jint(3))
reveal_type(s1)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.stream.IntStream"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
