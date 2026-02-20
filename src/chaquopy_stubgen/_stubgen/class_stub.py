"""ASM-based stub generation for a single Java class."""

from __future__ import annotations

import dataclasses
import logging

import jpype
import jpype.imports

from chaquopy_stubgen._stubgen.pysafe import pysafe, to_annotated_type, to_type_var_declaration
from chaquopy_stubgen._stubgen.sig_parser import (
    make_type_vars,
    parse_class_type_params,
    parse_field_type,
    parse_method_signature,
    parse_super_types,
)
from chaquopy_stubgen._stubgen.types import (
    ACC_BRIDGE,
    ACC_PROTECTED,
    ACC_PUBLIC,
    ACC_STATIC,
    ACC_SYNTHETIC,
    ACC_VARARGS,
    PARAMETER_TO_ARRAY_TYPE_MAP,
    ArgSig,
    JavaFunctionSig,
    TypeStr,
    TypeVarStr,
)
from chaquopy_stubgen._stubgen.whitelists import METHOD_CAN_RETURN_NONE

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Whitelist helpers
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
# Core helpers
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


def _count_typevar_uses(
    type_str: TypeStr, tv_names: set[str], counts: dict[str, int]
) -> None:
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


# ---------------------------------------------------------------------------
# Method stub generation
# ---------------------------------------------------------------------------


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
        method_type_vars, param_types, ret_type = parse_method_signature(
            str(m.signature) if m.signature else None,
            str(m.desc),
            usable_class_tvars if not is_static else [],
            is_constructor,
            scope_id=overload_scope,
        )

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

        # Java does not support keyword arguments; enforce positional-only calling
        # by inserting '/' after the last regular parameter.  '/' must come before
        # any *varargs entry, and is only added when at least one regular Java
        # parameter (not 'self', not *varargs) is present.
        regular_java_params = [a for a in sig.args if a.name != "self" and not a.var_args]
        if regular_java_params:
            varargs_idx = next(
                (i for i, arg in enumerate(sig.args) if arg.var_args),
                len(sig.args),
            )
            sig_parts.insert(varargs_idx, "/")

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


# ---------------------------------------------------------------------------
# Class stub generation
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class JavaClassPythonStub:
    imports: list[str]
    type_vars: list[
        str
    ]  # TypeVar declarations (module-level, before the class definition)
    code: list[str]


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
        raw_class_tvars, _ = parse_class_type_params(class_sig)
    class_type_vars = make_type_vars(raw_class_tvars, class_prefix)

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
            ft = parse_field_type(
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
        super_type_strs = parse_super_types(
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
