from .conftest import run_mypy
from pathlib import Path


def test_array_list_valid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list.add('42')

reveal_type(java_array_list)
reveal_type(java_array_list.get(0))
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:6: note: Revealed type is "java.util.ArrayList[builtins.str]"
testfile.py:7: note: Revealed type is "builtins.str"
Success: no issues found in 1 source file
""",
    )


def test_array_list_invalid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list.add(42)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: error: No overload variant of "add" of "ArrayList" matches argument type "int"  [call-overload]
testfile.py:4: note: Possible overload variants:
testfile.py:4: note:     def add(self, e: str) -> bool
testfile.py:4: note:     def add(self, int: int | jint | Integer, e: str) -> None
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )


def test_array_list_no_implicit_conversion(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

pylist = ['test', '1', '2']
java_array_list = ArrayList(pylist)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: error: No overload variant of "ArrayList" matches argument type "list[str]"  [call-overload]
testfile.py:4: note: Possible overload variants:
testfile.py:4: note:     def [_ArrayList__E] ArrayList(self) -> ArrayList[_ArrayList__E]
testfile.py:4: note:     def [_ArrayList__E] ArrayList(self, int: int | jint | Integer) -> ArrayList[_ArrayList__E]
testfile.py:4: note:     def [_ArrayList__E] ArrayList(self, collection: Collection[_ArrayList__E]) -> ArrayList[_ArrayList__E]
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )


def test_array_list_missing_type_annotation(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list = ArrayList(2)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:3: error: Need type annotation for "java_array_list"  [var-annotated]
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )


def test_array_list_no_getitem(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import ArrayList

java_array_list: ArrayList[str] = ArrayList()
java_array_list[0]
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: error: Value of type "ArrayList[str]" is not indexable  [index]
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )