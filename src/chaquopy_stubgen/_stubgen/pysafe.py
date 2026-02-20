"""Python name-mangling helpers and stub text output functions."""

from __future__ import annotations

import keyword

from chaquopy_stubgen._stubgen.types import TypeStr, TypeVarStr

EXTRA_RESERVED_WORDS = {"exec", "print"}  # Removed in Python 3.0


def is_reserved_word(word: str) -> bool:
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
