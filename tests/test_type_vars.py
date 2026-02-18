from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_staticmethod_typevar_only_once_in_return_type(mypy_project_dir: Path):
    code = """\
from java.util import Collections

comparator = Collections.reverseOrder()
reveal_type(comparator)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.Comparator[java.lang.Object]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_staticmethod_typevar_multiple_times_in_return_type(mypy_project_dir: Path):
    code = """\
from java.util.stream import Collectors

s = Collectors.toSet()  # *1
reveal_type(s)  # *2
"""

    expected_mypy_output = {
        "*1": 'error: Need type annotation for "s"',
        "*2": 'note: Revealed type is "java.util.stream.Collector[Any, java.lang.Object, java.util.Set[Any]]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_staticmethod_typevar_only_in_args(mypy_project_dir: Path):
    code = """\
from java.util import Comparator, Objects
from java.lang import String, Integer

cmp: Comparator[String] = String.CASE_INSENSITIVE_ORDER

str1 = String("Apple")
str2 = String("Banana")
result = Objects.compare(str1, str2, cmp)

num1 = Integer(10)
result = Objects.compare(str1, num1, cmp)  # *1

"""

    expected_mypy_output = {
        "*1": 'error: Cannot infer value of type parameter "_compare__T" of "compare" of "Objects"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
