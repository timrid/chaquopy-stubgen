from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_static_proxy_basic(mypy_project_dir: Path):
    code = """\
from java import constructor, static_proxy, method, jint, jdouble
from java.lang import String
from java.lang import Exception, InterruptedException

class MyClass(static_proxy()):  # type: ignore[misc]
    @constructor([])
    @constructor([jint])
    @constructor([jdouble], modifiers="public synchronized")
    @constructor((String,), throws=[Exception, InterruptedException])
    def __init__(self, value=None):
        super().__init__()
        self.value = str(value)

    @method(jint, [jint, jint])
    @method(jdouble, [jdouble, jdouble], modifiers="public synchronized")
    @method(String, (String, String), throws=[Exception, InterruptedException])
    def add(self, a, b):
        return a + b
"""

    expected_mypy_output = {}
    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_static_proxy_wrong_types(mypy_project_dir: Path):
    code = """\
import builtins
from java import constructor, static_proxy, method, jint, jdouble
from java.lang import String

class MyClass(static_proxy()):  # type: ignore[misc]
    @constructor([int])  # *1
    @constructor([float], modifiers=[])  # *2
    @constructor([str], throws=[int, builtins.Exception])  # *3
    def __init__(self, value=None):
        super().__init__()
        self.value = str(value)

    @method(int, [int, int])  # *4
    @method(float, [jdouble, jdouble], modifiers=[])  # *5
    @method(String, [str, String], throws=[int, builtins.Exception])  # *6
    def add(self, a, b):
        return a + b
"""
    expected_mypy_output: dict[str, str | list[str]] = {
        "*1": 'error: List item 0 has incompatible type "type[int]"; expected "type[Primitive] | type[Object]"',
        "*2": [
            'error: List item 0 has incompatible type "type[float]"; expected "type[Primitive] | type[Object]"',
            'error: Argument "modifiers" to "constructor" has incompatible type "list[Never]"; expected "str"',
        ],
        "*3": [
            'error: List item 0 has incompatible type "type[str]"; expected "type[Primitive] | type[Object]"',
            'error: List item 0 has incompatible type "type[int]"; expected "type[Throwable]"',
            'error: List item 1 has incompatible type "type[Exception]"; expected "type[Throwable]"',
        ],
        "*4": [
            'error: Argument 1 to "method" has incompatible type "type[int]"; expected "type[Primitive] | type[Object]"',
            'error: List item 0 has incompatible type "type[int]"; expected "type[Primitive] | type[Object]"',
            'error: List item 1 has incompatible type "type[int]"; expected "type[Primitive] | type[Object]"',
        ],
        "*5": [
            'error: Argument 1 to "method" has incompatible type "type[float]"; expected "type[Primitive] | type[Object]"',
            'error: Argument "modifiers" to "method" has incompatible type "list[Never]"; expected "str"',
        ],
        "*6": [
            'error: List item 0 has incompatible type "type[str]"; expected "type[Primitive] | type[Object]"',
            'error: List item 0 has incompatible type "type[int]"; expected "type[Throwable]"',
            'error: List item 1 has incompatible type "type[Exception]"; expected "type[Throwable]"',
        ],
    }
    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
