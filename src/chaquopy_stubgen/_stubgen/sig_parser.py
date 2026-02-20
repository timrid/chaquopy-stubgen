"""JVM generic-signature and descriptor parser."""

from __future__ import annotations

import dataclasses

from chaquopy_stubgen._stubgen.types import (
    PARAMETER_TO_ARRAY_TYPE_MAP,
    TYPE_NAME_TO_PRIMITIVE_MAP,
    TypeStr,
    TypeVarStr,
)


def _internal_to_dotted_raw(name: str) -> str:
    """Convert JVM internal name to dotted Java name, keeping '$' for later processing."""
    return name.replace("/", ".")


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


@dataclasses.dataclass
class _ParseResult:
    """Result of parsing a single type from a JVM generic signature."""

    type_str: TypeStr
    end: int  # index directly after the consumed characters


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
            PRIMITIVE_DESCS[c],
            is_argument=is_argument,
            is_array_param=is_array_param,
            is_type_arg=is_type_arg,
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


def parse_class_type_params(sig: str) -> tuple[list[tuple[str, TypeStr | None]], int]:
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


def make_type_vars(
    params: list[tuple[str, TypeStr | None]], scope_id: str
) -> list[TypeVarStr]:
    return [
        TypeVarStr(java_name=name, python_name=f"_{scope_id}__{name}", bound=bound)
        for name, bound in params
    ]


def parse_method_signature(
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
        raw_params, pos = parse_class_type_params(source)
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


def parse_field_type(
    sig: str | None, desc: str, type_vars: list[TypeVarStr]
) -> TypeStr:
    """Parse a field's type from its generic signature or plain descriptor."""
    source = sig if sig else desc
    result = _parse_type_signature(source, 0, type_vars)
    return result.type_str


def parse_super_types(
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
            _, pos = parse_class_type_params(sig)
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
