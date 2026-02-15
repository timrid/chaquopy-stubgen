from .conftest import run_mypy
from pathlib import Path


def test_bifunction_callback(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing

from java import dynamic_proxy
from java.util import HashMap
from java.util.function import BiConsumer


# if typing.TYPE_CHECKING:
K = typing.TypeVar("K")
V = typing.TypeVar("V")

class PyBiConsumer(BiConsumer[K, V]):
    def __init__(self, func: typing.Callable[[K, V], None]) -> None: ...
# else:
# 
#     class PyBiConsumer(dynamic_proxy(BiConsumer)):
#         def __init__(self, func) -> None:
#             super().__init__()
#             self.func = func
# 
#         def accept(self, k, v) -> None:
#             self.func(k, v)


def valid_for_each_cb(k: str, v: float) -> None:
    print(f"Key: {k}, Value: {v}")


def invalid_for_each_cb_1(k: str, v: str) -> None:
    print(f"Key: {k}, Value: {v}")


def invalid_for_each_cb_2(k: str) -> None:
    print(f"Key: {k}")


java_map: "HashMap[str, float]" = HashMap()
java_map.put("hello", 1.0)
java_map.put("world", 42.0)

java_map.forEach(PyBiConsumer(valid_for_each_cb))
java_map.forEach(
    PyBiConsumer(
        invalid_for_each_cb_1
    )
)
java_map.forEach(
    PyBiConsumer(
        invalid_for_each_cb_2
    )
)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:44: error: Argument 1 to "PyBiConsumer" has incompatible type "Callable[[str, str], None]"; expected "Callable[[str, float], None]"  [arg-type]
testfile.py:49: error: Argument 1 to "PyBiConsumer" has incompatible type "Callable[[str], None]"; expected "Callable[[str, float], None]"  [arg-type]
Found 2 errors in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )



def test_predicate_callback(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing

from java import dynamic_proxy
from java.util import ArrayList
from java.util.function import Predicate

# if typing.TYPE_CHECKING:
T = typing.TypeVar("T")

class PyPredicate(Predicate[T]):
    def __init__(self, func: typing.Callable[[T], bool]) -> None: ...
# else:
# 
#     class PyPredicate(dynamic_proxy(Predicate)):
#         def __init__(self, func) -> None:
#             super().__init__()
#             self.func = func
# 
#         def test(self, t) -> bool:
#             return self.func(t)


def valid_predicate(k: str) -> bool:
    return True


def invalid_predicate_1() -> bool:
    return False


def invalid_predicate_2(k: int) -> bool:
    return False


def invalid_predicate_3(k: str) -> int:
    return False


java_list: "ArrayList[str]" = ArrayList()
java_list.add("test")
java_list.add("1")
java_list.add("2")

java_list.removeIf(PyPredicate(valid_predicate))
java_list.removeIf(
    PyPredicate(
        invalid_predicate_1
    )
)
java_list.removeIf(
    PyPredicate(
        invalid_predicate_2
    )
)
java_list.removeIf(
    PyPredicate(
        invalid_predicate_3
    )
)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:47: error: Argument 1 to "PyPredicate" has incompatible type "Callable[[], bool]"; expected "Callable[[str], bool]"  [arg-type]
testfile.py:52: error: Argument 1 to "PyPredicate" has incompatible type "Callable[[int], bool]"; expected "Callable[[str], bool]"  [arg-type]
testfile.py:57: error: Argument 1 to "PyPredicate" has incompatible type "Callable[[str], int]"; expected "Callable[[str], bool]"  [arg-type]
Found 3 errors in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )


def test_stream_chaining_and_type_inference(stub_dir: Path, mypy_project_dir: Path):
    code = """\
import typing

from java import dynamic_proxy
from java.util import ArrayList
from java.util.concurrent.atomic import AtomicInteger
from java.util.function import Function, Predicate
from java.util.stream import Collectors

# if typing.TYPE_CHECKING:
T = typing.TypeVar("T")
R = typing.TypeVar("R")

class PyPredicate(Predicate[T]):
    def __init__(self, func: typing.Callable[[T], bool]) -> None: ...

class PyFunction(Function[T, R]):
    def __init__(self, func: typing.Callable[[T], R]) -> None: ...
# else:
# 
#     class PyPredicate(dynamic_proxy(Predicate)):
#         def __init__(self, func) -> None:
#             super().__init__()
#             self.func = func
# 
#         def test(self, t) -> bool:
#             return self.func(t)
# 
#     class PyFunction(dynamic_proxy(Function)):
#         def __init__(self, func) -> None:
#             super().__init__()
#             self.func = func
# 
#         def apply(self, t) -> typing.Any:
#             return self.func(t)


def map_str_to_int(v: str) -> int:
    return 0


def int_predicate(v: int) -> bool:
    return False


def str_predicate(v: str) -> bool:
    return False


def map_int_to_atomicint(v: int) -> AtomicInteger:
    return AtomicInteger(0)


def map_atomicint_to_bool(v: AtomicInteger) -> bool:
    return False


java_list: "ArrayList[str]" = ArrayList()
java_list.add("test")
java_list.add("1")
java_list.add("2")

str_stream = java_list.stream()
reveal_type(str_stream)

int_stream = str_stream.map(PyFunction(map_str_to_int))
reveal_type(int_stream)

int_stream.filter(
    PyPredicate(
        str_predicate
    )
)

int_stream_2 = int_stream.filter(PyPredicate(int_predicate))
reveal_type(int_stream_2)

int_stream_2.map(
    PyFunction(
        map_atomicint_to_bool
    )
)

atomicint_stream = int_stream_2.map(PyFunction(map_int_to_atomicint))
java_set = atomicint_stream.collect(Collectors.toSet())
reveal_type(
    java_set
)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:63: note: Revealed type is "java.util.stream.Stream[builtins.str]"
testfile.py:66: note: Revealed type is "java.util.stream.Stream[builtins.int]"
testfile.py:70: error: Argument 1 to "PyPredicate" has incompatible type "Callable[[str], bool]"; expected "Callable[[int], bool]"  [arg-type]
testfile.py:75: note: Revealed type is "java.util.stream.Stream[builtins.int]"
testfile.py:79: error: Argument 1 to "PyFunction" has incompatible type "Callable[[AtomicInteger], bool]"; expected "Callable[[int], bool]"  [arg-type]
testfile.py:86: note: Revealed type is "java.util.Set[java.util.concurrent.atomic.AtomicInteger]"
Found 2 errors in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )

