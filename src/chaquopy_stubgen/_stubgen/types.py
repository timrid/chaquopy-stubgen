"""Shared data classes and constants for the Java stub generator."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class TypeStr:
    name: str
    type_args: list["TypeStr"] | None = None


@dataclasses.dataclass(frozen=True)
class TypeVarStr:
    java_name: str
    python_name: str
    bound: TypeStr | None = None


@dataclasses.dataclass(frozen=True)
class ArgSig:
    name: str
    arg_type: TypeStr | None = None
    var_args: bool = False


@dataclasses.dataclass(frozen=True)
class JavaFunctionSig:
    name: str
    static: bool
    args: list[ArgSig]
    ret_type: TypeStr
    type_vars: list[TypeVarStr]




# ---------------------------------------------------------------------------
# ASM access-flag constants (from org.objectweb.asm.Opcodes)
# ---------------------------------------------------------------------------
ACC_PUBLIC = 0x0001
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_INTERFACE = 0x0200
ACC_ABSTRACT = 0x0400
ACC_SYNTHETIC = 0x1000
ACC_ANNOTATION = 0x2000
ACC_ENUM = 0x4000
ACC_BRIDGE = 0x0040
ACC_VARARGS = 0x0080


# ---------------------------------------------------------------------------
# Java primitive type definitions
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Primitive:
    java_primitive: str
    java_object: str
    python_primitive: str
    python_type: str


PRIMITIVES: list[Primitive] = [
    Primitive("void", "java.lang.Void", "java.jvoid", "None"),
    Primitive("byte", "java.lang.Byte", "java.jbyte", "int"),
    Primitive("short", "java.lang.Short", "java.jshort", "int"),
    Primitive("int", "java.lang.Integer", "java.jint", "int"),
    Primitive("long", "java.lang.Long", "java.jlong", "int"),
    Primitive("boolean", "java.lang.Boolean", "java.jboolean", "bool"),
    Primitive("double", "java.lang.Double", "java.jdouble", "float"),
    Primitive("float", "java.lang.Float", "java.jfloat", "float"),
    Primitive("char", "java.lang.Character", "java.jchar", "str"),
]

TYPE_NAME_TO_PRIMITIVE_MAP: dict[str, Primitive] = {
    **{p.java_primitive: p for p in PRIMITIVES},
    **{p.java_object: p for p in PRIMITIVES},
}

PARAMETER_TO_ARRAY_TYPE_MAP: dict[str, str] = {
    "java.jboolean": "java.chaquopy.JavaArrayJBoolean",
    "java.jbyte": "java.chaquopy.JavaArrayJByte",
    "java.jshort": "java.chaquopy.JavaArrayJShort",
    "java.jint": "java.chaquopy.JavaArrayJInt",
    "java.jlong": "java.chaquopy.JavaArrayJLong",
    "java.jfloat": "java.chaquopy.JavaArrayJFloat",
    "java.jdouble": "java.chaquopy.JavaArrayJDouble",
    "java.jchar": "java.chaquopy.JavaArrayJChar",
}
