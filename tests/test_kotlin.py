from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_list_builder_valid(mypy_project_dir: Path):
    """ListBuilder is a generic Kotlin stdlib class; basic operations should type-check."""
    code = """\
from kotlin.collections.builders import ListBuilder

lb: ListBuilder[str] = ListBuilder()
lb.add("hello")

reveal_type(lb)           # *1
reveal_type(lb.get(0))    # *2
reveal_type(lb.build())   # *3
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "kotlin.collections.builders.ListBuilder[builtins.str]"',
        "*2": 'note: Revealed type is "builtins.str"',
        "*3": 'note: Revealed type is "java.util.List[builtins.str]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_list_builder_invalid(mypy_project_dir: Path):
    """Type errors on ListBuilder should be reported correctly."""
    code = """\
from kotlin.collections.builders import ListBuilder

lb: ListBuilder[str] = ListBuilder()
lb.add(42)  # *1
"""

    expected_mypy_output = {
        "*1": (
            'error: No overload variant of "add" of "ListBuilder" matches argument type "int"\n'
            'hint: Possible overload variants:\n'
            'hint:     def add(self, str, /) -> bool\n'
            'hint:     def add(self, int | jint | Integer, str, /) -> None'
        ),
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_map_builder_valid(mypy_project_dir: Path):
    """MapBuilder is a generic Kotlin stdlib class; basic operations should type-check."""
    code = """\
from kotlin.collections.builders import MapBuilder

mb: MapBuilder[str, int] = MapBuilder()
mb.put("key", 1)

reveal_type(mb)               # *1
reveal_type(mb.get("key"))    # *2
reveal_type(mb.build())       # *3
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "kotlin.collections.builders.MapBuilder[builtins.str, builtins.int]"',
        "*2": 'note: Revealed type is "builtins.int"',
        "*3": 'note: Revealed type is "java.util.Map[builtins.str, builtins.int]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_map_builder_inner_class_companion(mypy_project_dir: Path):
    """MapBuilder.Companion is an inner class and should be accessible as an attribute."""
    code = """\
from kotlin.collections.builders import MapBuilder

reveal_type(MapBuilder.Companion)  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "MapBuilder.Companion?"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_map_entry_type_argument(mypy_project_dir: Path):
    """java.util.Map.Entry should appear correctly in type arguments (not as 'java.util.')."""
    code = """\
from kotlin.collections.builders import MapBuilder

mb: MapBuilder[str, int] = MapBuilder()
reveal_type(mb.getEntries())  # *1
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.Set[java.util.Map.Entry[builtins.str, builtins.int]]"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_dollar_methods_not_in_stub(mypy_project_dir: Path):
    """Kotlin-internal methods with '$' in their name must not appear in stubs."""
    code = """\
from kotlin.collections.builders import MapBuilder

mb: MapBuilder[str, int] = MapBuilder()
mb.addKey  # *1
"""

    # addKey$kotlin_stdlib is a Kotlin-internal method and must not appear in the stub.
    # mypy should report it as unknown (the type: ignore suppresses the error for the
    # test, but the marker confirms the line was actually reached without a stub parse error).
    expected_mypy_output = {
        "*1": 'error: "MapBuilder[str, int]" has no attribute "addKey"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
