import pathlib


def add_chaquopy_bindings_to_java_package(
    output_path: pathlib.Path, import_output: list[str], class_output: list[str]
):
    """Add the chaquopy api to the main 'java' package"""
    import_output.append("""\
from java.chaquopy import (
    cast,
    detach,
    jarray,
    jclass,
    set_import_enabled,
    dynamic_proxy,
    static_proxy,
    constructor,
    method,
    Override,
)""")
    import_output.append("""\
from java.primitive import (
    jvoid,
    jboolean,
    jbyte,
    jshort,
    jint,
    jlong,
    jfloat,
    jdouble,
    jchar,
)""")
    class_output.append("""\
__all__ = [
    "cast",
    "detach",
    "jarray",
    "jclass",
    "set_import_enabled",
    "dynamic_proxy",
    "static_proxy",
    "constructor",
    "method",
    "Override",
    "jvoid",
    "jboolean",
    "jbyte",
    "jshort",
    "jint",
    "jlong",
    "jfloat",
    "jdouble",
    "jchar",
]""")

    (output_path / "chaquopy.pyi").write_text(
        """\
import typing

from .primitive import (
    Primitive,
    jboolean,
    jbyte,
    jshort,
    jint,
    jlong,
    jfloat,
    jdouble,
    jchar,
)

from java.lang import Object, Throwable

# class.pxi #######################################################################################
def jclass(clsname: str) -> type[Object]: ...

# array.pxi #######################################################################################
_JAVA_OBJ = typing.Union[Primitive, Object]

JAVA_OBJ_T = typing.TypeVar("JAVA_OBJ_T", bound=_JAVA_OBJ)

class JavaArray(Object, typing.Sequence[JAVA_OBJ_T]):
    @typing.overload
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[JAVA_OBJ_T]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jboolean],
        length_or_value: typing.Union[int, typing.Sequence[bool]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jbyte],
        length_or_value: typing.Union[int, typing.Sequence[int]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jshort],
        length_or_value: typing.Union[int, typing.Sequence[int]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jint],
        length_or_value: typing.Union[int, typing.Sequence[int]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jlong],
        length_or_value: typing.Union[int, typing.Sequence[int]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jfloat],
        length_or_value: typing.Union[int, typing.Sequence[float]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jdouble],
        length_or_value: typing.Union[int, typing.Sequence[float]],
    ): ...
    @typing.overload
    def __init__(
        self: JavaArray[jchar],
        length_or_value: typing.Union[int, str],
    ): ...
    def __len__(self): ...
    @typing.overload
    def __getitem__(
        self,
        key: int,
    ) -> JAVA_OBJ_T: ...
    @typing.overload
    def __getitem__(
        self,
        key: slice,
    ) -> JavaArray[JAVA_OBJ_T]: ...
    def copy(self) -> JavaArray[JAVA_OBJ_T]: ...
    def __copy__(self) -> JavaArray[JAVA_OBJ_T]: ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: JAVA_OBJ_T,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[JAVA_OBJ_T],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jboolean],
        key: int,
        value: bool,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jboolean],
        key: slice,
        value: typing.Sequence[bool],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jbyte],
        key: int,
        value: int,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jbyte],
        key: slice,
        value: typing.Sequence[int],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jshort],
        key: int,
        value: int,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jshort],
        key: slice,
        value: typing.Sequence[int],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jint],
        key: int,
        value: int,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jint],
        key: slice,
        value: typing.Sequence[int],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jlong],
        key: int,
        value: int,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jlong],
        key: slice,
        value: typing.Sequence[int],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jfloat],
        key: int,
        value: float,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jfloat],
        key: slice,
        value: typing.Sequence[float],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jdouble],
        key: int,
        value: float,
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jdouble],
        key: slice,
        value: typing.Sequence[float],
    ): ...
    @typing.overload
    def __setitem__(
        self: JavaArray[jchar],
        key: typing.Union[int, slice],
        value: str,
    ): ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __add__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __radd__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __contains__(self, value: typing.Any): ...
    def __iter__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def __reversed__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def index(self, value: typing.Any, start: int = 0, stop: int = ...) -> int: ...
    def count(self, value: typing.Any) -> int: ...

@typing.overload
def jarray(
    element_type: typing.Type[JAVA_OBJ_T],
) -> typing.Type[JavaArray[JAVA_OBJ_T]]: ...
@typing.overload
def jarray(element_type: str) -> typing.Type[JavaArray[typing.Any]]: ...

# import.pxi #######################################################################################
def set_import_enabled(enable: bool): ...

# proxy.pxi #######################################################################################

T = typing.TypeVar("T")

@typing.overload
def dynamic_proxy(
    __i1: typing.Type[T],
) -> typing.Type[T]: ...
@typing.overload
def dynamic_proxy(
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
) -> typing.Type[typing.Any]: ...

JAVA_CLASS_T = typing.TypeVar("JAVA_CLASS_T", bound=Object)

@typing.overload
def static_proxy(
    extends: typing.Type[JAVA_CLASS_T],
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
    package: str | None = ...,
    modifiers: str = "public",
) -> typing.Type[JAVA_CLASS_T]: ...
@typing.overload
def static_proxy(
    extends: None = ...,
    # intersection of classes is not supported in type hints, so we use Any here
    *implements: typing.Type[typing.Any],
    package: str | None = ...,
    modifiers: str = "public",
) -> typing.Type[typing.Any]: ...
def constructor(
    arg_types: typing.Sequence[_JAVA_OBJ],
    *,
    modifiers: str = "public",
    throws: typing.Optional[typing.Sequence[Throwable]] = None,
): ...
def method(
    return_type: _JAVA_OBJ,
    arg_types: typing.Sequence[_JAVA_OBJ],
    *,
    modifiers: str = "public",
    throws: typing.Optional[typing.Sequence[Throwable]] = None,
): ...
def Override(
    return_type: _JAVA_OBJ,
    arg_types: typing.Sequence[_JAVA_OBJ],
    *,
    modifiers: str = "public",
    throws: typing.Optional[typing.Sequence[Throwable]] = None,
): ...

# utils.pxi #######################################################################################
def cast(cls: typing.Type[T], obj: typing.Any) -> T: ...

# jvm.pxi #######################################################################################
def detach() -> None: ...
""",
        encoding="utf-8",
    )

    (output_path / "primitive.pyi").write_text(
        """\
import typing

class Primitive:
    def __repr__(self): ...
    def __eq__(self, other): ...
    def __hash__(self): ...
    def __lt__(self, other): ...

class jvoid(Primitive):
    def __init__(self): ...

class jboolean(Primitive):
    def __init__(self, value: typing.Any): ...

class NumericPrimitive(Primitive): ...

class IntPrimitive(NumericPrimitive):
    def __init__(self, value: int, truncate: bool = False): ...

class jbyte(IntPrimitive): ...
class jshort(IntPrimitive): ...
class jint(IntPrimitive): ...
class jlong(IntPrimitive): ...

class FloatPrimitive(NumericPrimitive):
    def __init__(self, value: typing.Union[float, int], truncate: bool = False): ...

class jfloat(FloatPrimitive): ...
class jdouble(FloatPrimitive): ...

class jchar(Primitive):
    def __init__(self, value): ...
""",
        encoding="utf-8",
    )
