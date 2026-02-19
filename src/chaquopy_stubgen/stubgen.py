"""
ASM-based Java stub generator.

Generates Python type stubs from Java .class files using the ASM bytecode library,
without requiring a running JVM with the target classes loaded (only ASM itself is needed).
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import keyword
import logging
import multiprocessing
import shutil
import zipfile
from pathlib import Path

import jpype
import jpype.imports

from chaquopy_stubgen.chaquopy_bindings import add_chaquopy_bindings_to_java_package
from chaquopy_stubgen.whitelists import METHOD_CAN_RETURN_NONE


log = logging.getLogger(__name__)


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


EXTRA_RESERVED_WORDS = {"exec", "print"}  # Removed in Python 3.0


def is_reserved_word(word):
    return keyword.iskeyword(word) or word in EXTRA_RESERVED_WORDS


def pysafe(s: str) -> str | None:
    """
    Given an identifier name in Java, return an equivalent identifier name in
    Python that is guaranteed to not collide with the Python grammar.

    """
    if s.startswith("__") and s.endswith("__") and len(s) >= 4:
        # Dunder methods should not be considered safe.
        # (see system defined names in the Python documentation
        # https://docs.python.org/3/reference/lexical_analysis.html#reserved-classes-of-identifiers
        # )
        return None
    if is_reserved_word(s):
        return s + "_"
    return s


def pysafe_package_path(package_path: str) -> str:
    """Apply the JPype package name mangling. Segments which would clash with a python keyword are suffixed by '_'."""
    return ".".join([pysafe(p) or "" for p in package_path.split(".")])


def to_annotated_type(
    type_name: TypeStr,
    package_name: str,
    classes_done: set[str],
    types_used: set[str],
    imports_output: list[str],
    can_be_deferred: bool = True,
) -> str:
    """
    Convert a python type, represented as a TypeStr, to the actual textual stub file output.

    This takes into account:
     - mangling of package and type names (suffix python keywords with '_')
     - adding imports if necessary
     - using either a standard plain `Type`, a forward `'Type'`, or a `fully.qualified.package.Type`
     - recursively writing out type arguments, if any.
     - convert "typing.Union" with multiple type args to the more concise "A | B | C" syntax.
    """
    a_type = type_name.name
    if "." in a_type and a_type != "typing.Union":
        a_type = pysafe_package_path(a_type)
        types_used.add(a_type)
        a_type_parent, _, local_type = a_type.rpartition(".")
        if a_type_parent == "builtins":
            a_type = local_type
        elif a_type_parent == pysafe_package_path(package_name):
            if local_type in classes_done:
                a_type = local_type
            elif can_be_deferred:
                a_type = local_type
            else:
                # use fully qualified name - add import to our own domain
                own_package = a_type.partition(".")[0]
                imports_output.append(f"import {own_package}")
        else:
            imports_output.append(f"import {a_type_parent}")
    a_type = a_type.replace("$", ".")
    if type_name.type_args or a_type == "":
        type_args = [
            to_annotated_type(t, package_name, classes_done, types_used, imports_output)
            for t in type_name.type_args or []
        ]
        if a_type == "typing.Union":
            return " | ".join(type_args)
        return f"{a_type}[{', '.join(type_args)}]"
    else:
        return a_type


def to_type_var_declaration(
    type_var: TypeVarStr,
    package_name: str,
    classes_done: set[str],
    types_used: set[str],
    imports_output: list[str],
) -> str:
    """Convert a python type variable, represented as a TypeVarStr, to the actual textual stub file output."""
    imports_output.append("import typing")
    if type_var.bound is not None:
        return (
            "{pyname} = typing.TypeVar('{pyname}', bound={bound})  # <{jname}>".format(
                pyname=type_var.python_name,
                bound=to_annotated_type(
                    type_var.bound,
                    package_name,
                    classes_done,
                    types_used,
                    imports_output,
                ),
                jname=type_var.java_name,
            )
        )
    else:
        return "{pyname} = typing.TypeVar('{pyname}')  # <{jname}>".format(
            pyname=type_var.python_name, jname=type_var.java_name
        )


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
# JVM generic-signature parser
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _ParseResult:
    """Result of parsing a single type from a JVM generic signature."""

    type_str: TypeStr
    end: int  # index directly after the consumed characters


def _internal_to_dotted(name: str) -> str:
    """Convert JVM internal name (slashes) to dotted Java name."""
    return name.replace("/", ".").replace("$", ".")


def _internal_to_dotted_raw(name: str) -> str:
    """Convert JVM internal name to dotted Java name, keeping '$' for later processing."""
    return name.replace("/", ".")


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


def translate_type_name(
    type_name: str,
    type_args: list[TypeStr] | None = None,
    is_argument: bool = False,
    is_array_param: bool = False,
    is_type_arg: bool = False,
) -> TypeStr:
    """
    Translate basic Java types to python types. Note that this conversion is applied for ALL types, no matter if they
    appear as method argument types, field types, return types, super types, etc.

    Converted types in all cases:
     - Java primitives (e.g. int) and Java boxed primitives (e.g. Integer)
     - Java void -> None
     - java.lang.String -> str, but ONLY IF JPype convertStrings flag is enabled
     - java.lang.Object -> Any
     - java.lang.Class -> Type

    Additionally, implicitConversions=True indicates that the type is used as METHOD ARGUMENT. In this case we also
    apply the mangling by handleImplicitConversions() to account for JPype implicit type conversions.
    """
    union: list[TypeStr] = []

    if type_name in TYPE_NAME_TO_PRIMITIVE_MAP:
        primitive = TYPE_NAME_TO_PRIMITIVE_MAP[type_name]
        if is_array_param and is_argument:
            raise ValueError(
                f"Type {type_name} cannot be both an array parameter and an argument type."
            )

        if is_array_param:
            union.append(TypeStr(primitive.python_primitive))
        elif is_type_arg:
            union.append(TypeStr(primitive.java_object))
        else:
            union.append(TypeStr(primitive.python_type))

        if is_argument:
            # implicit conversions
            union.append(TypeStr(primitive.python_primitive))
            union.append(TypeStr(primitive.java_object))

    if type_name == "java.lang.String":
        if is_array_param or is_type_arg:
            union.append(TypeStr("java.lang.String"))
        else:
            union.append(TypeStr("str"))
            if is_argument:
                union.append(TypeStr("java.lang.String"))
    if type_name == "java.lang.Class":
        union.append(TypeStr("typing.Type", type_args))
    if type_name == "java.lang.Object":
        union.append(TypeStr("java.lang.Object"))
        if is_argument:
            union.append(TypeStr("int"))
            union.append(TypeStr("bool"))
            union.append(TypeStr("float"))
            union.append(TypeStr("str"))

    if len(union) == 1:
        return TypeStr(union[0].name, union[0].type_args)
    if len(union) > 1:
        return TypeStr("typing.Union", union)
    return TypeStr(type_name, type_args)


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


def _parse_type_signature(
    sig: str,
    pos: int,
    type_vars: list[TypeVarStr],
    is_argument: bool = False,
    is_array_param: bool = False,
    is_type_arg: bool = False,
) -> _ParseResult:
    """
    Parse a single Java type starting at *pos* in the generic signature string *sig*.
    Returns a _ParseResult with the parsed TypeStr and the new position.

    Handles:
      - base types: B C D F I J S V Z
      - object types: L<name>;  and L<name><type-args>;
      - arrays: [<type>
      - type variables: T<name>;
      - wildcards: * + - (inside type argument lists)
    """
    c = sig[pos]

    # ---- primitive / void ---------------------------------------------------
    PRIMITIVE_DESCS = {
        "B": "byte",
        "C": "char",
        "D": "double",
        "F": "float",
        "I": "int",
        "J": "long",
        "S": "short",
        "V": "void",
        "Z": "boolean",
    }
    if c in PRIMITIVE_DESCS:
        ts = translate_type_name(
            PRIMITIVE_DESCS[c], is_argument=is_argument, is_array_param=is_array_param, is_type_arg=is_type_arg
        )
        return _ParseResult(ts, pos + 1)

    # ---- array --------------------------------------------------------------
    if c == "[":
        elem = _parse_type_signature(
            sig, pos + 1, type_vars, is_argument=False, is_array_param=True
        )
        # Mimic translate_java_array_type logic
        if elem.type_str.name in PARAMETER_TO_ARRAY_TYPE_MAP:
            arr_ts = TypeStr(PARAMETER_TO_ARRAY_TYPE_MAP[elem.type_str.name])
        else:
            arr_ts = TypeStr("java.chaquopy.JavaArray", [elem.type_str])
        return _ParseResult(arr_ts, elem.end)

    # ---- type variable  T<name>; -------------------------------------------
    if c == "T":
        end = sig.index(";", pos + 1)
        var_name = sig[pos + 1 : end]
        matching = [tv for tv in type_vars if tv.java_name == var_name]
        if matching:
            ts = TypeStr(matching[0].python_name)
        else:
            ts = TypeStr(var_name)
        return _ParseResult(ts, end + 1)

    # ---- wildcard (inside < >) ----------------------------------------------
    if c == "*":
        return _ParseResult(TypeStr("java.lang.Object"), pos + 1)
    if c in ("+", "-"):
        # bounded wildcard — use the bound type directly (same as reflection code)
        inner = _parse_type_signature(sig, pos + 1, type_vars)
        return _ParseResult(inner.type_str, inner.end)

    # ---- object type  L<classname>[<typeargs>]; ----------------------------
    if c == "L":
        # find the end of the class name (either '<' or ';')
        i = pos + 1
        while i < len(sig) and sig[i] not in ("<", ";", "."):
            i += 1
        class_name = _internal_to_dotted_raw(sig[pos + 1 : i])
        type_args: list[TypeStr] | None = None

        if i < len(sig) and sig[i] == "<":
            # parse type arguments
            i += 1  # skip '<'
            type_args = []
            while sig[i] != ">":
                arg_result = _parse_type_signature(sig, i, type_vars, is_type_arg=True)
                type_args.append(arg_result.type_str)
                i = arg_result.end
            i += 1  # skip '>'

        # skip any inner-class suffix  .InnerName<...>  (treat as outer for now)
        while i < len(sig) and sig[i] == ".":
            i += 1
            while i < len(sig) and sig[i] not in ("<", ";", "."):
                i += 1
            if i < len(sig) and sig[i] == "<":
                i += 1
                depth = 1
                while depth > 0:
                    if sig[i] == "<":
                        depth += 1
                    elif sig[i] == ">":
                        depth -= 1
                    i += 1

        assert sig[i] == ";", f"Expected ';' at {i} in {sig!r}"
        i += 1  # skip ';'

        ts = translate_type_name(
            class_name,
            type_args=type_args,
            is_argument=is_argument,
            is_array_param=is_array_param,
            is_type_arg=is_type_arg,
        )
        return _ParseResult(ts, i)

    raise ValueError(f"Unexpected character {c!r} at pos {pos} in signature {sig!r}")


def _parse_descriptor_type(
    desc: str, pos: int, is_argument: bool = False, is_array_param: bool = False
) -> _ParseResult:
    """Parse a single type from a plain (non-generic) method descriptor."""
    return _parse_type_signature(
        desc, pos, [], is_argument=is_argument, is_array_param=is_array_param
    )


def _parse_class_type_params(sig: str) -> tuple[list[tuple[str, TypeStr | None]], int]:
    """
    Parse the formal type parameter declarations at the start of a class or method
    signature, e.g. ``<K:Ljava/lang/Enum<TK;>;V:Ljava/lang/Object;>``.

    Returns a list of (java_name, bound) and the position after '>'.
    At this point type_vars are not yet known so we parse bounds without resolving
    type var names (they will be resolved once TypeVarStr objects are created).
    """
    if not sig or sig[0] != "<":
        return [], 0

    params: list[tuple[str, TypeStr | None]] = []
    i = 1
    while sig[i] != ">":
        # read name up to ':'
        colon = sig.index(":", i)
        name = sig[i:colon]
        i = colon + 1
        # There may be a class bound (L...) or just interface bounds (starts with ':')
        # A lone ':' means no class bound
        bound: TypeStr | None = None
        if i < len(sig) and sig[i] != ":" and sig[i] != ">":
            result = _parse_type_signature(sig, i, [])
            raw_bound = result.type_str
            if raw_bound.name not in ("java.lang.Object", "None"):
                bound = raw_bound
            i = result.end
        # skip interface bounds (additional ':' separated)
        while i < len(sig) and sig[i] == ":":
            i += 1
            if i < len(sig) and sig[i] not in (":", ">"):
                result = _parse_type_signature(sig, i, [])
                i = result.end
        params.append((name, bound))
    return params, i + 1  # skip '>'


def _make_type_vars(
    params: list[tuple[str, TypeStr | None]], scope_id: str
) -> list[TypeVarStr]:
    return [
        TypeVarStr(java_name=name, python_name=f"_{scope_id}__{name}", bound=bound)
        for name, bound in params
    ]


def _parse_method_signature(
    sig: str | None,
    desc: str,
    type_vars: list[TypeVarStr],
    is_constructor: bool,
    scope_id: str = "",
) -> tuple[list[TypeVarStr], list[TypeStr], TypeStr]:
    """
    Parse a method signature/descriptor.

    Returns (method_type_vars, param_types, return_type).
    Uses *sig* (generic) if available, otherwise falls back to *desc* (raw descriptor).
    *scope_id* is used to build TypeVar python names (e.g. ``_methodName__T``).
    """
    method_type_vars: list[TypeVarStr] = []
    param_types: list[TypeStr] = []

    source = sig if sig else desc
    pos = 0

    # optional method-level type parameters <T:...>
    if source[0] == "<":
        raw_params, pos = _parse_class_type_params(source)
        method_type_vars = [
            TypeVarStr(java_name=name, python_name=f"_{scope_id}__{name}", bound=bound)
            for name, bound in raw_params
        ]
    all_type_vars = method_type_vars + type_vars

    assert source[pos] == "(", f"Expected '(' at {pos} in {source!r}"
    pos += 1

    while source[pos] != ")":
        result = _parse_type_signature(source, pos, all_type_vars, is_argument=True)
        param_types.append(result.type_str)
        pos = result.end

    pos += 1  # skip ')'

    if is_constructor:
        ret_type = TypeStr("None")
    else:
        result = _parse_type_signature(source, pos, all_type_vars, is_argument=False)
        ret_type = result.type_str

    return method_type_vars, param_types, ret_type


def _parse_field_type(
    sig: str | None, desc: str, type_vars: list[TypeVarStr]
) -> TypeStr:
    """Parse a field's type from its generic signature or plain descriptor."""
    source = sig if sig else desc
    result = _parse_type_signature(source, 0, type_vars)
    return result.type_str


def _parse_super_types(
    sig: str | None,
    super_name: str | None,
    interfaces: list[str],
    type_vars: list[TypeVarStr],
) -> list[TypeStr]:
    """
    Parse the superclass and interface types of a class.
    Uses the generic signature when available.
    """
    if sig:
        # skip class type params if present
        pos = 0
        if sig[0] == "<":
            _, pos = _parse_class_type_params(sig)
        supers: list[TypeStr] = []
        while pos < len(sig):
            result = _parse_type_signature(sig, pos, type_vars)
            supers.append(result.type_str)
            pos = result.end
        return supers
    else:
        supers = []
        if super_name:
            supers.append(translate_type_name(_internal_to_dotted_raw(super_name)))
        for iface in interfaces:
            supers.append(translate_type_name(_internal_to_dotted_raw(iface)))
        return supers


# ---------------------------------------------------------------------------
# Whitelist helper
# ---------------------------------------------------------------------------


def _method_whitelist_key(
    class_name_dotted: str, method_name: str, param_descs: list[str]
) -> str:
    """Build the whitelist key in the format used by METHOD_CAN_RETURN_NONE."""
    params = ", ".join(param_descs)
    return f"{class_name_dotted}.{method_name}({params})"


def _desc_to_whitelist_type(desc_char: str, class_name: str = "") -> str:
    """Convert a single descriptor character (or 'L...;') to a whitelist type string."""
    MAP = {
        "B": "byte",
        "C": "char",
        "D": "double",
        "F": "float",
        "I": "int",
        "J": "long",
        "S": "short",
        "V": "void",
        "Z": "boolean",
    }
    if desc_char in MAP:
        return MAP[desc_char]
    if desc_char.startswith("["):
        inner = _desc_to_whitelist_type(desc_char[1:], class_name)
        return inner + "[]"
    if desc_char.startswith("L"):
        return desc_char[1:].rstrip(";").replace("/", ".").replace("$", ".")
    return desc_char


def _parse_descriptor_params_for_whitelist(desc: str) -> list[str]:
    """Parse raw descriptor parameter types for whitelist lookup."""
    assert desc[0] == "("
    i = 1
    params = []
    while desc[i] != ")":
        if desc[i] == "[":
            j = i
            while desc[j] == "[":
                j += 1
            if desc[j] == "L":
                end = desc.index(";", j)
                params.append(_desc_to_whitelist_type(desc[i : end + 1]))
                i = end + 1
            else:
                params.append(_desc_to_whitelist_type(desc[i : j + 1]))
                i = j + 1
        elif desc[i] == "L":
            end = desc.index(";", i)
            params.append(_desc_to_whitelist_type(desc[i : end + 1]))
            i = end + 1
        else:
            params.append(_desc_to_whitelist_type(desc[i]))
            i += 1
    return params


# ---------------------------------------------------------------------------
# Output dataclass (same as before)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class JavaClassPythonStub:
    imports: list[str]
    type_vars: list[
        str
    ]  # TypeVar declarations (module-level, before the class definition)
    code: list[str]


# ---------------------------------------------------------------------------
# Core: generate stubs for one class from its ClassNode
# ---------------------------------------------------------------------------


def _is_accessible(access: int) -> bool:
    return bool(access & (ACC_PUBLIC | ACC_PROTECTED))


def _get_param_names_from_local_vars(m) -> list[str] | None:
    """
    Extract parameter names from the MethodNode's localVariables table.
    localVariables index 0 = 'this' (for instance methods), then params in order.
    Returns None if no local variable debug info is available.
    """
    from org.objectweb.asm import Type as AsmType  # type: ignore

    if not m.localVariables:
        return None
    is_static = bool(m.access & ACC_STATIC)
    # Build index -> name map
    lv_map: dict[int, str] = {}
    for lv in m.localVariables:
        lv_map[int(lv.index)] = str(lv.name)
    # For instance methods, slot 0 = 'this', params start at slot 1
    # For static methods, params start at slot 0
    # But long/double take 2 slots — we need to count carefully using the descriptor
    arg_types = list(AsmType.getArgumentTypes(str(m.desc)))
    names: list[str] = []
    slot = 0 if is_static else 1  # skip 'this'
    for at in arg_types:
        names.append(lv_map.get(slot, ""))
        # long (J) and double (D) occupy 2 slots
        slot += 2 if at.getSort() in (7, 8) else 1  # Sort.LONG=7, Sort.DOUBLE=8
    return names if any(names) else None


def _count_typevar_uses(type_str: TypeStr, tv_names: set[str], counts: dict[str, int]) -> None:
    """Recursively count how many times each TypeVar name appears in a TypeStr tree."""
    if type_str.name in tv_names:
        counts[type_str.name] = counts.get(type_str.name, 0) + 1
    for arg in type_str.type_args or []:
        _count_typevar_uses(arg, tv_names, counts)


def _substitute_typestr(type_str: TypeStr, subs: dict[str, TypeStr]) -> TypeStr:
    """Replace TypeVar names with their substitution TypeStr, recursively."""
    if type_str.name in subs:
        return subs[type_str.name]
    if type_str.type_args:
        new_args = [_substitute_typestr(a, subs) for a in type_str.type_args]
        return TypeStr(type_str.name, new_args)
    return type_str


def _eliminate_single_use_type_vars(
    method_type_vars: list[TypeVarStr],
    param_types: list[TypeStr],
    ret_type: TypeStr,
) -> tuple[list[TypeVarStr], list[TypeStr], TypeStr]:
    """
    Remove method-level TypeVars that appear only once across all parameter types
    and the return type.  Such TypeVars add no constraint and only create noise in
    the stub output.  Each eliminated TypeVar is replaced by its bound, or by
    java.lang.Object if it has no bound.

    Returns (kept_type_vars, new_param_types, new_ret_type).
    """
    tv_names = {tv.python_name for tv in method_type_vars}
    counts: dict[str, int] = {}
    for pt in param_types:
        _count_typevar_uses(pt, tv_names, counts)
    _count_typevar_uses(ret_type, tv_names, counts)

    subs: dict[str, TypeStr] = {}
    kept: list[TypeVarStr] = []
    for tv in method_type_vars:
        if counts.get(tv.python_name, 0) <= 1:
            subs[tv.python_name] = tv.bound if tv.bound else TypeStr("java.lang.Object")
        else:
            kept.append(tv)

    if subs:
        param_types = [_substitute_typestr(p, subs) for p in param_types]
        ret_type = _substitute_typestr(ret_type, subs)
        method_type_vars = kept

    return method_type_vars, param_types, ret_type


def _generate_method_stub_asm(
    package_name: str,
    method_name_py: str,
    methods: list,  # list of MethodNode
    classes_done: set[str],
    classes_used: set[str],
    class_type_vars: list[TypeVarStr],
    class_name_dotted: str,
    output: list[str],
    imports_output: list[str],
    scope_id_prefix: str,
) -> None:
    """Generate stubs for one method name (possibly overloaded) using ASM data."""
    from org.objectweb.asm import Type as AsmType  # type: ignore

    is_constructor = method_name_py == "__init__"
    is_overloaded = len(methods) > 1

    # Sort by param count then param types for deterministic output
    def sort_key(m):
        arg_types = list(AsmType.getArgumentTypes(m.desc))
        return (len(arg_types), str(m.desc))

    signatures: list[JavaFunctionSig] = []
    for i, m in enumerate(sorted(methods, key=sort_key)):
        is_static = bool(m.access & ACC_STATIC)
        is_varargs = bool(m.access & ACC_VARARGS)

        overload_scope = f"{scope_id_prefix}_{i}" if is_overloaded else scope_id_prefix

        # Parse with the correct scope_id so TypeVar python names are right from the start
        usable_class_tvars = class_type_vars
        method_type_vars, param_types, ret_type = _parse_method_signature(
            str(m.signature) if m.signature else None,
            str(m.desc),
            usable_class_tvars if not is_static else [],
            is_constructor,
            scope_id=overload_scope,
        )
        # For non-static methods, combine method TVars with class TVars for resolving
        # Note: _parse_method_signature already used the right combined list internally.
        # We only need the final lists here for building ArgSig/ret annotations.

        # Eliminate method-level TypeVars that appear only once across all params
        # and the return type — they add no constraint and just create noise.
        if method_type_vars:
            method_type_vars, param_types, ret_type = _eliminate_single_use_type_vars(
                method_type_vars, param_types, ret_type
            )

        # Try to get real parameter names from debug info
        param_names = _get_param_names_from_local_vars(m)

        # Build arg list
        args: list[ArgSig] = [] if is_static else [ArgSig(name="self")]
        for idx, pt in enumerate(param_types):
            is_last = idx == len(param_types) - 1
            is_va = is_varargs and is_last
            if is_va:
                # varargs: unwrap the array type
                if pt.name == "java.chaquopy.JavaArray" and pt.type_args:
                    pt = pt.type_args[0]
                elif pt.name in PARAMETER_TO_ARRAY_TYPE_MAP.values():
                    pass  # leave as-is — rare
            # Use real param name from debug info, otherwise arg1/arg2/...
            if param_names and idx < len(param_names) and param_names[idx]:
                arg_name = param_names[idx]
            else:
                arg_name = f"arg{idx + 1}"
            args.append(ArgSig(name=arg_name, arg_type=pt, var_args=is_va))

        # Whitelist check
        wl_params = _parse_descriptor_params_for_whitelist(str(m.desc))
        wl_key = _method_whitelist_key(class_name_dotted, str(m.name), wl_params)
        if wl_key in METHOD_CAN_RETURN_NONE:
            ret_type = TypeStr("typing.Union", [ret_type, TypeStr("None")])

        signatures.append(
            JavaFunctionSig(
                name=method_name_py,
                args=args,
                ret_type=ret_type,
                static=is_static,
                type_vars=method_type_vars,
            )
        )

    # Emit type var declarations first (before @overload decorators)
    for sig in signatures:
        for tv in sig.type_vars:
            output.append(
                to_type_var_declaration(
                    tv, package_name, classes_done, classes_used, imports_output
                )
            )

    for sig in signatures:
        if is_overloaded:
            imports_output.append("import typing")
            output.append("@typing.overload")
        if sig.static:
            output.append("@staticmethod")

        sig_parts: list[str] = []
        for idx, arg in enumerate(sig.args):
            if arg.name == "self":
                sig_parts.append("self")
            else:
                safe_name = pysafe(arg.name)
                if safe_name is None:
                    safe_name = f"invalidArgName{idx}"
                if arg.var_args:
                    safe_name = "*" + safe_name
                if arg.arg_type:
                    safe_name += ": " + to_annotated_type(
                        arg.arg_type,
                        package_name,
                        classes_done,
                        classes_used,
                        imports_output,
                    )
                sig_parts.append(safe_name)

        if is_constructor:
            output.append(f"def __init__({', '.join(sig_parts)}) -> None: ...")
        else:
            fn_name = pysafe(sig.name)
            if fn_name is None:
                continue
            ret_str = to_annotated_type(
                sig.ret_type, package_name, classes_done, classes_used, imports_output
            )
            output.append(f"def {fn_name}({', '.join(sig_parts)}) -> {ret_str}: ...")


def convert_java_class_to_python_stub(
    class_file: str,
    class_data: bytes,
    all_class_data: dict[str, bytes] | None = None,
    classes_done: set[str] | None = None,
    classes_used: set[str] | None = None,
    parent_type_vars: list[TypeVarStr] | None = None,
) -> JavaClassPythonStub:
    """
    Convert a Java .class file to a Python stub using ASM (no Java Reflection).
    """
    from org.objectweb.asm import ClassReader  # type: ignore
    from org.objectweb.asm.tree import ClassNode  # type: ignore

    if classes_done is None:
        classes_done = set()
    if classes_used is None:
        classes_used = set()

    cr = ClassReader(jpype.JArray(jpype.JByte)(class_data))  # type: ignore
    cn = ClassNode()
    cr.accept(cn, 0)

    # Skip synthetic classes and anonymous/local classes (those with outerMethod set).
    # Inner classes with '$' are only called recursively from their outer class;
    # convert_jar_to_python_stubs only passes top-level (no '$') files at the top level.
    acc = int(cn.access)
    if acc & ACC_SYNTHETIC:
        return JavaClassPythonStub(imports=[], type_vars=[], code=[])

    if cn.outerMethod:
        return JavaClassPythonStub(imports=[], type_vars=[], code=[])

    raw_class_name = str(cn.name)  # e.g. "java/util/ArrayList"
    package_internal = raw_class_name.rsplit("/", 1)[0] if "/" in raw_class_name else ""
    package_name = package_internal.replace("/", ".")
    simple_name = raw_class_name.rsplit("/", 1)[-1]  # e.g. "ArrayList" or "Map$Entry"
    class_name_dotted = raw_class_name.replace("/", ".").replace("$", ".")
    display_name = simple_name.split("$")[-1]  # Python class name (no outer prefix)

    # Unique scope id for TypeVars
    class_prefix = simple_name.replace("$", "__")

    # Parse class-level type parameters
    class_sig = str(cn.signature) if cn.signature else None
    raw_class_tvars: list[tuple[str, TypeStr | None]] = []
    if class_sig and class_sig[0] == "<":
        raw_class_tvars, _ = _parse_class_type_params(class_sig)
    class_type_vars = _make_type_vars(raw_class_tvars, class_prefix)

    # For non-static inner classes, the outer class's TypeVars are also in scope.
    # Determine whether this class is a static nested class via its InnerClasses entry.
    is_static_inner = True
    if parent_type_vars is not None:
        for _ic in cn.innerClasses:
            if (
                str(_ic.name) == raw_class_name
                and (str(_ic.outerName) if _ic.outerName else None) != raw_class_name
            ):
                is_static_inner = bool(int(_ic.access) & ACC_STATIC)
                break
    if parent_type_vars and not is_static_inner:
        usable_type_vars = parent_type_vars + class_type_vars
    else:
        usable_type_vars = class_type_vars

    import_output: list[str] = []

    # ---- Fields ----
    fields_output: list[str] = []
    for f in cn.fields:
        if not (f.access & ACC_PUBLIC) and not (f.access & ACC_PROTECTED):
            continue
        if f.access & ACC_SYNTHETIC:
            continue
        field_name = str(f.name)
        safe_field_name = pysafe(field_name)
        if safe_field_name is None:
            continue
        field_is_static = bool(f.access & ACC_STATIC)
        try:
            ft = _parse_field_type(
                str(f.signature) if f.signature else None,
                str(f.desc),
                usable_type_vars if not field_is_static else [],
            )
        except Exception as e:
            log.warning(f"Skipping field {class_name_dotted}.{field_name}: {e}")
            continue
        ann = to_annotated_type(
            ft, package_name, classes_done, classes_used, import_output
        )
        if field_is_static:
            import_output.append("import typing")
            ann = f"typing.ClassVar[{ann}]"
        fields_output.append(f"{safe_field_name}: {ann} = ...")

    # ---- Constructors ----
    constructors_output: list[str] = []
    ctors = [
        m
        for m in cn.methods
        if str(m.name) == "<init>"
        and (m.access & (ACC_PUBLIC | ACC_PROTECTED))
        and not (m.access & (ACC_SYNTHETIC | ACC_BRIDGE))
    ]
    if ctors:
        try:
            _generate_method_stub_asm(
                package_name,
                "__init__",
                ctors,
                classes_done,
                classes_used,
                usable_type_vars,
                class_name_dotted,
                constructors_output,
                import_output,
                scope_id_prefix="__init__",
            )
        except Exception as e:
            log.warning(f"Skipping constructors of {class_name_dotted}: {e}")

    # ---- Methods ----
    methods_output: list[str] = []
    # Group by name
    method_groups: dict[str, list] = {}
    for m in cn.methods:
        mname = str(m.name)
        if mname == "<init>" or mname == "<clinit>":
            continue
        if not (m.access & (ACC_PUBLIC | ACC_PROTECTED)):
            continue
        if m.access & (ACC_SYNTHETIC | ACC_BRIDGE):
            continue
        py_name = pysafe(mname)
        if py_name is None:
            continue
        method_groups.setdefault(py_name, []).append(m)

    for py_name, overloads in sorted(method_groups.items()):
        try:
            _generate_method_stub_asm(
                package_name,
                py_name,
                overloads,
                classes_done,
                classes_used,
                usable_type_vars,
                class_name_dotted,
                methods_output,
                import_output,
                scope_id_prefix=py_name,
            )
        except Exception as e:
            log.warning(f"Skipping method {class_name_dotted}.{py_name}: {e}")

    # ---- Super types ----
    super_name = str(cn.superName) if cn.superName else None
    interfaces = [str(i) for i in cn.interfaces]

    # For interfaces the JVM always writes java/lang/Object as the synthetic
    # super_name in the bytecode, but interfaces DO expose Object's methods at
    # runtime — every interface instance IS an Object.  Keep it so that interface
    # stubs satisfy bound=java.lang.Object (e.g. for JavaArray[T]).

    try:
        super_type_strs = _parse_super_types(
            class_sig, super_name, interfaces, usable_type_vars
        )
    except Exception as e:
        log.warning(f"Could not parse supers for {class_name_dotted}: {e}")
        super_type_strs = []

    super_type_annotations: list[str] = []
    for st in super_type_strs:
        # Drop java.lang.Object when it would not be the sole supertype — all
        # other supertypes (classes and interfaces alike) already transitively
        # inherit from Object.  Keeping it first would violate Python's C3 MRO
        # whenever any listed interface also inherits from Object.
        if st.name == "java.lang.Object" and len(super_type_strs) > 1:
            continue
        try:
            ann = to_annotated_type(
                st,
                package_name,
                classes_done,
                classes_used,
                import_output,
                can_be_deferred=False,
            )
            super_type_annotations.append(ann)
        except Exception as e:
            log.warning(f"Skipping super type {st} for {class_name_dotted}: {e}")

    # Add typing.Generic[...] if the class has type parameters
    if class_type_vars:
        import_output.append("import typing")
        generic_args = ", ".join(tv.python_name for tv in class_type_vars)
        super_type_annotations.append(f"typing.Generic[{generic_args}]")

    # Special case: Throwable → add builtins.Exception (mirrors chaquopy_customizer_super_types)
    if class_name_dotted == "java.lang.Throwable":
        super_type_annotations.append("builtins.Exception")
        import_output.append("import builtins")

    super_str = (
        f"({', '.join(super_type_annotations)})" if super_type_annotations else ""
    )

    # ---- Nested (inner) classes ----
    # Find direct inner classes of this class via the InnerClasses attribute and
    # generate their stubs recursively, embedding them inside this class body.
    nested_classes_output: list[str] = []
    nested_type_var_lines: list[str] = []
    nested_done: set[str] = set()
    if all_class_data is not None:
        for ic in cn.innerClasses:
            ic_name = str(ic.name)
            ic_outer_name = str(ic.outerName) if ic.outerName else None
            ic_inner_name = str(ic.innerName) if ic.innerName else None
            ic_access = int(ic.access)
            # Only direct inner classes of THIS class
            if ic_outer_name != raw_class_name:
                continue
            # Skip anonymous inner classes (no innerName)
            if not ic_inner_name:
                continue
            # Skip synthetic inner classes
            if ic_access & ACC_SYNTHETIC:
                continue
            # Skip non-public/protected inner classes
            if not (ic_access & (ACC_PUBLIC | ACC_PROTECTED)):
                continue
            ic_data = all_class_data.get(ic_name)
            if ic_data is None:
                continue
            ic_is_static = bool(ic_access & ACC_STATIC)
            ic_parent_tvars = usable_type_vars if not ic_is_static else None
            try:
                ic_done = set(classes_done)
                nested_stub = convert_java_class_to_python_stub(
                    ic_name + ".class",
                    ic_data,
                    all_class_data=all_class_data,
                    classes_done=ic_done,
                    classes_used=classes_used,
                    parent_type_vars=ic_parent_tvars,
                )
                nested_done |= ic_done
            except Exception as e:
                log.warning(f"Skipping nested class {ic_name}: {e}")
                continue
            import_output.extend(nested_stub.imports)
            nested_type_var_lines.extend(nested_stub.type_vars)
            # Indent the nested class code by one level; blank lines stay blank
            for line in nested_stub.code:
                nested_classes_output.append(("    " + line) if line.strip() else "")
    classes_done |= nested_done

    # ---- TypeVar declarations (own class only; nested TypeVars are in nested_type_var_lines) ----
    own_type_var_lines: list[str] = []
    for tv in class_type_vars:
        own_type_var_lines.append(
            to_type_var_declaration(
                tv, package_name, classes_done, classes_used, import_output
            )
        )
    # All TypeVar declarations go to module level (before the outermost class definition)
    all_type_var_lines = own_type_var_lines + nested_type_var_lines

    # ---- Assemble class ----
    has_body = (
        fields_output or constructors_output or methods_output or nested_classes_output
    )
    class_code: list[str] = []
    if has_body:
        class_code.append(f"class {display_name}{super_str}:")
        for line in fields_output:
            class_code.append(f"    {line}")
        for line in constructors_output:
            class_code.append(f"    {line}")
        for line in methods_output:
            class_code.append(f"    {line}")
        for line in nested_classes_output:
            class_code.append(line)  # already indented
    else:
        class_code.append(f"class {display_name}{super_str}: ...")

    classes_done.add(display_name)

    # Separate TypeVars from class code so the caller can place them at module level.
    # The leading blank separator goes with type_vars if present, otherwise with code.
    if all_type_var_lines:
        return JavaClassPythonStub(
            imports=import_output,
            type_vars=[""] + all_type_var_lines,
            code=class_code,
        )
    else:
        return JavaClassPythonStub(
            imports=import_output,
            type_vars=[],
            code=[""] + class_code,
        )


# ---------------------------------------------------------------------------
# Package-level driver (mirrors generate_stubs_for_java_package)
# ---------------------------------------------------------------------------

DEFAULT_CLASSPATH = ["asm-9.6.jar", "asm-tree-9.6.jar"]


def _worker_init(jvmpath: str | None, log_level: int) -> None:
    """Start a JVM in this worker process and register shutdown via atexit."""
    import atexit

    import jpype  # type: ignore
    import jpype.imports  # type: ignore

    logging.basicConfig(level=log_level)
    jpype.startJVM(jvmpath=jvmpath, classpath=DEFAULT_CLASSPATH)
    atexit.register(jpype.shutdownJVM)


def _process_package(
    package_dir: str,
    class_files: list[str],
    package_class_data: dict[str, bytes],
    output_dir: Path,
) -> None:
    """Process one Java package and write its __init__.pyi."""
    import time

    top_level_files = [f for f in class_files if "$" not in Path(f).stem]
    t0 = time.perf_counter()
    log.info(
        f"Processing package {package_dir} "
        f"({len(top_level_files)} top-level / {len(class_files)} total classes)..."
    )

    # Pre-populate with all top-level class names so that intra-package
    # references (e.g., superclass) always use the short name regardless
    # of alphabetical processing order (e.g., D before P).
    classes_done: set[str] = {Path(f).stem for f in top_level_files}
    classes_used: set[str] = set()
    combined_imports: set[str] = set()
    combined_code: list[str] = []

    for class_file in sorted(top_level_files):
        try:
            stub = convert_java_class_to_python_stub(
                class_file,
                package_class_data[class_file[:-6]],
                all_class_data=package_class_data,
                classes_done=classes_done,
                classes_used=classes_used,
            )
        except Exception as e:
            log.warning(f"Skipping {class_file}: {e}")
            continue
        combined_imports.update(stub.imports)
        combined_code.extend(stub.type_vars)  # module-level TypeVar declarations
        combined_code.extend(stub.code)  # class definition

    if package_dir == "java":
        add_chaquopy_bindings_to_java_package(
            output_dir / "java", combined_imports, combined_code
        )

    output_file = output_dir / Path(package_dir) / "__init__.pyi"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        for imp in sorted(combined_imports):
            f.write(imp + "\n")
        f.write("\n\n")
        for line in combined_code:
            f.write(line + "\n")

    elapsed = time.perf_counter() - t0
    log.info(f"Finished package {package_dir} in {elapsed:.2f}s")


def convert_jar_to_python_stubs(
    jar_file_path: Path, output_dir: Path, jvmpath: str | None = None
) -> None:
    """
    Extract all .class files from the given JAR file and convert them to Python stubs.
    Produces a directory tree with __init__.pyi files.
    """
    if len(output_dir.resolve().parts) < 3:
        raise ValueError(
            f"output_dir '{output_dir}' is dangerously close to the filesystem root, "
            "refusing to delete it."
        )
    shutil.rmtree(output_dir, ignore_errors=True)

    with zipfile.ZipFile(jar_file_path, "r") as jar:
        class_entries = [e for e in jar.namelist() if e.endswith(".class")]

        # Group by package directory and pre-read all class data so workers
        # don't need to access the ZIP concurrently.
        packages: dict[str, list[str]] = {}
        for class_file in class_entries:
            package_dir = str(Path(class_file).parent)
            packages.setdefault(package_dir, []).append(class_file)

        all_class_data: dict[str, dict[str, bytes]] = {
            package_dir: {f[:-6]: jar.read(f) for f in class_files}
            for package_dir, class_files in packages.items()
        }

    # Ensure the "java" package is present so that the base chaquopy bindings are generated.
    packages.setdefault("java", [])
    all_class_data.setdefault("java", {})

    # Each worker process gets its own JVM instance, achieving true parallelism
    # unhindered by the GIL.  All data passed to workers is plain bytes/strings
    # (fully picklable) so spawn-based multiprocessing works fine on macOS.
    # "spawn" is used explicitly (instead of the Linux default "fork") because
    # forking a process with a running JVM causes undefined behaviour in JPype.
    mp_context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        initializer=_worker_init,
        initargs=(jvmpath, log.getEffectiveLevel()),
        mp_context=mp_context,
    ) as pool:
        futures = [
            pool.submit(
                _process_package,
                package_dir,
                class_files,
                all_class_data[package_dir],
                output_dir,
            )
            for package_dir, class_files in packages.items()
        ]
        for future in concurrent.futures.as_completed(futures):
            if exc := future.exception():
                log.error(f"Package processing failed: {exc}")
