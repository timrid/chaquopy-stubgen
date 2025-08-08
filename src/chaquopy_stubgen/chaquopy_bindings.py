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
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[JAVA_OBJ_T]],
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
    def __eq__(self, other: typing.Any) -> bool: ...
    def __add__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __radd__(self, other: JavaArray[JAVA_OBJ_T]) -> JavaArray[JAVA_OBJ_T]: ...
    def __contains__(self, value: typing.Any): ...
    def __iter__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def __reversed__(self) -> typing.Iterator[JAVA_OBJ_T]: ...
    def index(self, value: typing.Any, start: int = 0, stop: int = ...) -> int: ...
    def count(self, value: typing.Any) -> int: ...

# inference of correct type is not working, when overloading __init__ with mypy v1.15.0
class JavaArrayJBoolean(JavaArray[jboolean]):
    def __init__(
        self,
        length_or_value: typing.Union[
            int, typing.Sequence[typing.Union[jboolean, bool]]
        ],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jboolean, bool],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jboolean, bool]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJByte(JavaArray[jbyte]):
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[typing.Union[jbyte, int]]],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jbyte, int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jbyte, int]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJShort(JavaArray[jshort]):
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[typing.Union[jshort, int]]],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jshort, int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jshort, int]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJInt(JavaArray[jint]):
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[typing.Union[jint, int]]],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jint, int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jint, int]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJLong(JavaArray[jlong]):
    def __init__(
        self,
        length_or_value: typing.Union[int, typing.Sequence[typing.Union[jlong, int]]],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jlong, int],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jlong, int]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJFloat(JavaArray[jfloat]):
    def __init__(
        self,
        length_or_value: typing.Union[
            int, typing.Sequence[typing.Union[jfloat, float]]
        ],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jfloat, float],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jfloat, float]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJDouble(JavaArray[jdouble]):
    def __init__(
        self,
        length_or_value: typing.Union[
            int, typing.Sequence[typing.Union[jdouble, float]]
        ],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: typing.Union[jdouble, float],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Sequence[typing.Union[jdouble, float]],
    ): ...
    def __buffer__(self, flags: int, /) -> memoryview: ...

class JavaArrayJChar(JavaArray[jchar]):
    def __init__(
        self,
        length_or_value: typing.Union[
            int, typing.Sequence[typing.Union[jchar, str]], str
        ],
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: int,
        value: str,
    ): ...
    @typing.overload
    def __setitem__(
        self,
        key: slice,
        value: typing.Union[typing.Sequence[typing.Union[jchar, str]], str],
    ): ...
    

@typing.overload
def jarray(
    element_type: typing.Type[jboolean],
) -> typing.Type[JavaArrayJBoolean]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jbyte],
) -> typing.Type[JavaArrayJByte]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jshort],
) -> typing.Type[JavaArrayJShort]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jint],
) -> typing.Type[JavaArrayJInt]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jlong],
) -> typing.Type[JavaArrayJLong]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jfloat],
) -> typing.Type[JavaArrayJFloat]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jdouble],
) -> typing.Type[JavaArrayJDouble]: ...
@typing.overload
def jarray(
    element_type: typing.Type[jchar],
) -> typing.Type[JavaArrayJChar]: ...
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
