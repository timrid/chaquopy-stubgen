from .conftest import run_mypy
from pathlib import Path


def test_enum_map_valid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing
from java.util import EnumMap
from java.util.concurrent import TimeUnit

timeunit_enummap: "EnumMap[TimeUnit, typing.Any]" = EnumMap(TimeUnit)
reveal_type(timeunit_enummap)

timeunit_enummap.put(TimeUnit.SECONDS, 'test')
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:6: note: Revealed type is "java.util.EnumMap[java.util.concurrent.TimeUnit, Any]"
Success: no issues found in 1 source file
""",
    )


def test_enum_map_invalid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing
from java.util import EnumMap
from java.util.concurrent import TimeUnit

timeunit_enummap: "EnumMap[TimeUnit, typing.Any]" = EnumMap(TimeUnit)

timeunit_enummap.put(42, 'test')

timeunit_enummap.put('fail', 'test')
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:7: error: Argument 1 to "put" of "EnumMap" has incompatible type "int"; expected "TimeUnit"  [arg-type]
testfile.py:9: error: Argument 1 to "put" of "EnumMap" has incompatible type "str"; expected "TimeUnit"  [arg-type]
Found 2 errors in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )
