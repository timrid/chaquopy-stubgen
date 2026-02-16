from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_hash_map_valid(mypy_project_dir: Path):
    code = """\
from java.util import HashMap

java_map: "HashMap[str, float]" = HashMap()
java_map.put("hello", 1.0)
java_map.put("world", 42.0)

reveal_type(java_map)  # *1
reveal_type(java_map.values())  # *2
reveal_type(java_map.keySet())  # *3

reveal_type(java_map.get('hello'))  # *4

java_map.put('test1', 42)
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.util.HashMap[builtins.str, builtins.float]"',
        "*2": 'note: Revealed type is "java.util.Collection[builtins.float]"',
        "*3": 'note: Revealed type is "java.util.Set[builtins.str]"',
        "*4": 'note: Revealed type is "builtins.float"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_hash_map_invalid(mypy_project_dir: Path):
    code = """\
from java.util import HashMap

java_map: "HashMap[str, float]" = HashMap()
java_map.put("hello", 1.0)
java_map.put("world", 42.0)

java_map.put('test1', 'foo')  # *1
"""

    expected_mypy_output = {
        "*1": 'error: Argument 2 to "put" of "HashMap" has incompatible type "str"; expected "float"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
