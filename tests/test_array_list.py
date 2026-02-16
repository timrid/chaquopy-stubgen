from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_array_list_valid(mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list.add('42')

reveal_type(java_array_list)  # *1
reveal_type(java_array_list.get(0))  # *2
"""

    expected_mypy_output = {
        "*1": '''\
note: Revealed type is "java.util.ArrayList[builtins.str]"''',
        "*2": '''\
note: Revealed type is "builtins.str"''',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_array_list_invalid(mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list.add(42)  # *1
"""

    expected_mypy_output = {
        "*1": """\
error: No overload variant of "add" of "ArrayList" matches argument type "int"
hint: Possible overload variants:
hint:     def add(self, e: str) -> bool
hint:     def add(self, int: int | jint | Integer, e: str) -> None""",
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_array_list_no_implicit_conversion(mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

pylist = ['test', '1', '2']
java_array_list = ArrayList(pylist)  # *1
"""

    expected_mypy_output = {
        "*1": """\
error: No overload variant of "ArrayList" matches argument type "list[str]"
hint: Possible overload variants:
hint:     def [_ArrayList__E] ArrayList(self) -> ArrayList[_ArrayList__E]
hint:     def [_ArrayList__E] ArrayList(self, int: int | jint | Integer) -> ArrayList[_ArrayList__E]
hint:     def [_ArrayList__E] ArrayList(self, collection: Collection[_ArrayList__E]) -> ArrayList[_ArrayList__E]""",
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_array_list_missing_type_annotation(mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list = ArrayList(2)  # *1
"""

    expected_mypy_output = {
        "*1": 'error: Need type annotation for "java_array_list"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_array_list_no_getitem(mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list[0]  # *1
"""

    expected_mypy_output = {
        "*1": 'error: Value of type "ArrayList[str]" is not indexable',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
