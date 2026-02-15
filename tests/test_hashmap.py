from .conftest import run_mypy
from pathlib import Path


def test_hash_map_valid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import HashMap

java_map: "HashMap[str, float]" = HashMap()
java_map.put("hello", 1.0)
java_map.put("world", 42.0)

reveal_type(java_map)
reveal_type(java_map.values())
reveal_type(java_map.keySet())

reveal_type(java_map.get('hello'))

java_map.put('test1', 42)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:7: note: Revealed type is "java.util.HashMap[builtins.str, builtins.float]"
testfile.py:8: note: Revealed type is "java.util.Collection[builtins.float]"
testfile.py:9: note: Revealed type is "java.util.Set[builtins.str]"
testfile.py:11: note: Revealed type is "builtins.float"
Success: no issues found in 1 source file
""",
    )


def test_hash_map_invalid(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.util import HashMap

java_map: "HashMap[str, float]" = HashMap()
java_map.put("hello", 1.0)
java_map.put("world", 42.0)

java_map.put('test1', 'foo')
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:7: error: Argument 2 to "put" of "HashMap" has incompatible type "str"; expected "float"  [arg-type]
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )


