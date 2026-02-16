from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_enum_map_valid(mypy_project_dir: Path):
    code = """\
import typing
from java.util import EnumMap
from java.util.concurrent import TimeUnit

timeunit_enummap: "EnumMap[TimeUnit, typing.Any]" = EnumMap(TimeUnit)
reveal_type(timeunit_enummap)  # *1

timeunit_enummap.put(TimeUnit.SECONDS, 'test')
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.EnumMap[java.util.concurrent.TimeUnit, Any]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_enum_map_invalid(mypy_project_dir: Path):
    code = """\
import typing
from java.util import EnumMap
from java.util.concurrent import TimeUnit

timeunit_enummap: "EnumMap[TimeUnit, typing.Any]" = EnumMap(TimeUnit)

timeunit_enummap.put(42, 'test')  # *1

timeunit_enummap.put('fail', 'test')  # *2
"""

    expected_mypy_output = {
        "*1": 'error: Argument 1 to "put" of "EnumMap" has incompatible type "int"; expected "TimeUnit"',
        "*2": 'error: Argument 1 to "put" of "EnumMap" has incompatible type "str"; expected "TimeUnit"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
