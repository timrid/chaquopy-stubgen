"""chaquopy-stubgen
A PEP484 python stub generator for Java modules using the Chaquopy import system.
Originally based on mypy stubgenc and stubgenj.

Copyright (c) CERN 2020-2021
Copyright (c) Tim Riddemann 2025

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Authors:
    M. Hostettler   <michi.hostettler@cern.ch>
    P. Elson        <philip.elson@cern.ch>
    T. Riddermann
"""

import collections
import dataclasses
import keyword
import logging
import pathlib
import re
from typing import Any, Generator, Union

import jpype

from chaquopy_stubgen.chaquopy_bindings import add_chaquopy_bindings_to_java_package

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


@dataclasses.dataclass(frozen=True)
class Javadoc:
    description: str
    ctors: str = ""
    methods: dict[str, str] = dataclasses.field(default_factory=dict)
    fields: dict[str, str] = dataclasses.field(default_factory=dict)


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


def is_pseudo_package(package: jpype.JPackage) -> bool:
    """
    Return True if the package is an (empty) "pseudo package" - a package that neither contains classes,
    nor sub-packages.

    Such packages are not importable in Java. Still, JPype can generate them e.g. for directories that are only present
    in Javadoc JARs but not in source JARs (e.g. "class-use" in Guava)
    """
    return len(dir(package)) == 0 or "$" in package.__name__


def package_and_sub_packages(
    package: jpype.JPackage,
) -> Generator[jpype.JPackage, None, None]:
    """Walk the java package tree and collect all packages in the JVM which are descendants of the given package."""
    yield package
    for name in dir(package):
        try:
            item = getattr(package, name)
            if isinstance(item, jpype.JPackage) and not is_pseudo_package(item):
                yield from package_and_sub_packages(item)
        except Exception as e:
            log.warning(f"skipping {package.__name__}.{name}: {e}")


def generate_java_stubs(
    parent_packages: list[jpype.JPackage],
    output_dir: Union[str, pathlib.Path] = ".",
    include_javadoc: bool = True,
) -> None:
    """
    Main entry point. Recursively generate stubs for the provided packages and all sub-packages.
    This method assumes that a JPype JVM was started with a proper classpath and the JPype import system is enabled.

    Errors in stub generation are treated in a lenient way; failing to generate stubs for one or more java classes
    will not stop stub generation for other classes.
    """
    packages: dict[str, jpype.JPackage] = {}
    for pkg in parent_packages:
        packages.update({pkg.__name__: pkg for pkg in package_and_sub_packages(pkg)})

    log.info(f"Collected {len(packages)} packages ...")

    # Map package names to a set of direct subpackages
    # (e.g {'foo.bar': {'wibble', 'wobble'}}).
    subpackages = collections.defaultdict(set)
    output_path = pathlib.Path(output_dir)
    # Prepare a dictionary for *all* package names (including the parents of
    # the actual packages that we wish to generate stubs for) which maps to the
    # path of the appropriate __init__.pyi stubfile.
    stubfile_packages_paths: dict[str, pathlib.Path] = {}
    for pkg_name in packages:
        pkg_parts = pkg_name.split(".")

        submodule_path = output_path
        submodule_name = ""
        for pkg_part in pkg_parts:
            if not submodule_name:
                submodule_path = submodule_path / f"{pkg_part}-stubs"
            else:
                submodule_path = submodule_path / pkg_part

            if not submodule_name:
                submodule_name = pkg_part
            else:
                submodule_name += f".{pkg_part}"

            if "." in submodule_name:
                parent, name = submodule_name.rsplit(".", 1)
                subpackages[parent].add(name)

            stubfile_packages_paths[submodule_name] = submodule_path / "__init__.pyi"

    for pkg_name, stubfile_path in stubfile_packages_paths.items():
        stubfile_path.parent.mkdir(parents=True, exist_ok=True)

        pkg = packages.get(pkg_name)
        if pkg is not None:
            generate_stubs_for_java_package(
                pkg, stubfile_path, sorted(subpackages[pkg_name]), include_javadoc
            )


def filter_class_names_in_package(package_name: str, types: set[str]) -> set[str]:
    """From the provided list of class names, filter and return those which are DIRECT descendants of the package"""
    local_types: set[str] = set()
    for typ in types:
        type_package, _, local_name = typ.rpartition(".")
        if type_package == package_name and "$" not in local_name:
            local_types.add(local_name)
    return local_types


def package_classes(package: jpype.JPackage) -> Generator[jpype.JClass]:
    """Collect and return all classes which are DIRECT descendants of the given package."""
    for name in dir(package):
        try:
            item: jpype.JClass = getattr(package, name)
            if isinstance(item, jpype.JClass):
                yield item
        except Exception as e:
            log.warning(f"skipping class {package.__name__}.{name}: {e}")


def provide_customizer_stubs(
    customizers_used: set[type], import_output: list[str], output_file: pathlib.Path
) -> None:
    """Write stubs for used JPype customizers."""
    # in the future, JPype (2.0?) will support customizers loaded from JAR files, inaccessible without the run-time
    # import system of JPype. Once this happens, we will have to extract the stubs and dump them to the file system
    # here.
    # But for the time being, keep things simple and just add an import ...
    for c in customizers_used:
        import_output.append(f"from {c.__module__} import {c.__qualname__}")


def generate_stubs_for_java_package(
    package: jpype.JPackage,
    output_file: pathlib.Path,
    subpackages: list[str],
    include_javadoc=False,
) -> None:
    """Generate stubs for a single Java package, represented as a python package with a single __init__ module."""
    pkg_name = package.__name__
    java_classes = sorted(package_classes(package), key=lambda pkg: pkg.__name__)
    log.info(
        f"Generating stubs for {pkg_name} ({len(java_classes)} classes, {len(subpackages)} subpackages)"
    )

    import_output: list[str] = []
    class_output: list[str] = []

    classes_done: set[str] = set()
    classes_used: set[str] = set()
    classes_failed: set[str] = set()
    customizers_used: set[type] = set()
    while java_classes:
        java_classes_to_generate = [
            c for c in java_classes if dependencies_satisfied(package, c, classes_done)
        ]
        if not java_classes_to_generate:
            # some inner class cases - will generate them with full names
            java_classes_to_generate = java_classes
        for cls in sorted(java_classes_to_generate, key=lambda c: c.__name__):
            try:
                generate_java_class_stub(
                    package,
                    cls,
                    include_javadoc,
                    classes_done,
                    classes_used,
                    customizers_used,
                    output=class_output,
                    imports_output=import_output,
                )
            # exception during class loading e.g. missing dependencies
            # (spark...)
            except jpype.JException as e:
                log.warning(f"Skipping {cls} due to {e}")
                classes_failed.add(simple_class_name_of(cls))
            java_classes.remove(cls)
        # Collect all classes in this java package which are referenced by other class stubs, but have not yet been
        # generated. To avoid unsatisfied type references in the stubs, we have to generate stubs for them:
        #  - first, we attempt to get them by explicitly reading the attribute from the JPackage object. This may work
        #    for certain protected or module internal (Java 11) classes.
        #  - failing that, we generate an empty stub.
        missing_private_classes = (
            filter_class_names_in_package(pkg_name, classes_used) - classes_done
        )
        for missing_private_class in sorted(missing_private_classes):
            cls = None
            try:
                if missing_private_class not in classes_failed:
                    cls = getattr(package, missing_private_class, None)
            # exception during class loading e.g. missing dependencies
            # (spark...)
            except jpype.JException as e:
                log.warning(
                    f"Skipping missing class {missing_private_class} due to {e}"
                )

            if cls is not None:
                if cls not in java_classes:
                    java_classes.append(cls)
            else:
                # This can happen if a public class refers to a private or package-private class directly,
                # e.g. as return type. In Java, such return values are not accessible:
                #   public class OuterClass {
                #      public static InnerClass test() {
                #          return new InnerClass();
                #      }
                #      private static class InnerClass {
                #          public void foo() { }
                #      }
                #   }
                #
                # From another class:
                #    OuterClass.test() - works
                #    OuterClass.InnerClass variable = OuterClass.test() - does not work
                #    OuterClass.test().foo() - does not work
                #
                # So the way to mimic this behavior in the stubs is to generate an empty "fake" stub for the private
                # class "OuterClass.InnerClass".
                log.warning(
                    f"reference to missing class {missing_private_class} - generating empty stub"
                )
                class_output.append("")
                generate_empty_class_stub(
                    missing_private_class,
                    classes_done=classes_done,
                    output=class_output,
                )

    for subpackage_name in subpackages:
        import_output.append(f"import {pkg_name}.{subpackage_name}")

    if customizers_used:
        provide_customizer_stubs(customizers_used, import_output, output_file)

    if pkg_name == "java":
        add_chaquopy_bindings_to_java_package(
            output_file.parent, import_output, class_output
        )

    output = []

    for line in sorted(set(import_output)):
        output.append(line)

    output.extend([""] * 2)
    for line in class_output:
        output.append(line)
    with open(output_file, "w", encoding="utf-8") as file:
        for line in output:
            file.write(f"{line}\n")


def simple_class_name_of(j_class: jpype.JClass) -> str:
    return str(j_class.class_.getName()).split(".")[-1]


def is_java_class(obj: type) -> bool:
    """Check if a type is a 'real' Java class. This excludes synthetic/anonymous Java classes."""
    if not isinstance(obj, jpype.JClass) or not hasattr(obj, "class_"):
        return False
    if (
        obj.class_.isAnonymousClass()
        or obj.class_.isLocalClass()
        or obj.class_.isSynthetic()
    ):
        return False
    return True


def dependencies_satisfied(
    package: jpype.JPackage, j_class: jpype.JClass, done: set[str]
):
    """
    Check if all supertypes of the provided class and any inner classes are already generated.
    In python, unlike in Java, the definition order of classes within a module matters.
    """
    try:
        super_types = [python_type(b) for b in java_super_types(j_class)]
    # exception during class loading of superclasses e.g. missing dependencies
    # (spark...)
    except jpype.JException:
        return False
    for super_type in super_types:
        super_type_name = super_type.name
        super_type_module = super_type_name[: super_type_name.rindex(".")]
        if super_type_module == package.__name__:
            super_type_local_name = super_type_name[len(super_type_module) + 1 :]
            if super_type_local_name not in done:
                return False
    # check dependencies of nested classes
    obj_dict = vars(j_class)
    for member in obj_dict.values():
        if is_java_class(member):
            if not dependencies_satisfied(package, member, done):
                return False
    return True


def java_super_types(j_class: jpype.JClass) -> list[Any]:
    """Get all supertypes of the provided Java class, up to java.lang.Object"""
    super_types = [j_class.class_.getGenericSuperclass()] + list(
        j_class.class_.getGenericInterfaces()
    )
    if (
        super_types[0] is None
    ):  #  or super_types[0].getTypeName() == "java.lang.Object":
        del super_types[0]
    return super_types


def is_method_present_in_java_lang_object(jMethod: Any) -> bool:
    """
    Checks is a particular method signature is present on java.lang.Object.
    This is used to find the method to call on java FunctionalInterfaces, as according to the JLS [1], these methods
    are excluded from the "1 abstract method" rule of functional interfaces.

    [1] https://docs.oracle.com/javase/specs/jls/se8/html/jls-9.html#jls-9.8
    """
    from java.lang import Object  # type: ignore

    try:
        Object.class_.getDeclaredMethod(jMethod.getName(), jMethod.getParameterTypes())
        return True
    except jpype.JException:  # java NoSuchMethodException
        return False


def invoked_method_on_functional_interface(j_class: Any) -> Any:
    """Get the actual java method to be invoked on a Java FunctionalInterface"""
    for j_method in j_class.getDeclaredMethods():
        if (
            is_public(j_method)
            and is_abstract(j_method)
            and not is_static(j_method)
            and not j_method.isSynthetic()
            and not is_method_present_in_java_lang_object(j_method)
        ):
            return j_method


def resolve_functional_Interface_method_type(
    j_type: Any, class_type_params: list[Any], type_args: list[TypeStr] | None
):
    if j_type in class_type_params and type_args is not None:
        # it is a type variable - resolve to the actual type argument
        idx = class_type_params.index(j_type)
        return type_args[idx]
    else:
        # it is something else (e.g. a java type) - resolve in the usual way
        return python_type(j_type)


def mangle_callable_type_args(
    j_class: Any, type_args: list[TypeStr] | None
) -> list[TypeStr] | None:
    """
    Generate sensible type arguments for typing.Callable.

    The JPype customizer that maps java FunctionalInterface to python Callable is a special story when it comes to
    generic type arguments.

    Since FunctionalInterfaces in Java are classes, type arguments are given at the class level, e.g.
    ```java
    @FunctionalInterface
    public interface Comparator<T> {
        int compare(T o1, T o2);
    }
    ```
    However, the type arguments for typing.Callable depend BOTH on the type arguments of the class AND the signature
    of the (only) method in the FunctionalInterface, e.g.
    ```python
    typing.Callable[[T, T], int]
    ```
    for the above example.

    TODO - NOT IMPLEMENTED YET:
    To make things even more complicated, FunctionalInterface classes can inherit from other FunctionalInterfaces,
    fixing or specifying certain type parameters:
    ```java
    @FunctionalInterface
    public interface BinaryOperator<T> extends BiFunction<T,T,T> {  }

    @FunctionalInterface
    public interface BiFunction<T, U, R> {
        R apply(T t, U u);
    }
    ```
    which should result in
    ```python
    typing.Callable[[T, T], T]
    ```

    """
    invoked_method = invoked_method_on_functional_interface(j_class)
    if invoked_method is None:
        return None  # TODO: implement inheritance case ...
    j_class_type_parameters = list(j_class.getTypeParameters())
    resolved_param_types = [
        resolve_functional_Interface_method_type(
            paramType, j_class_type_parameters, type_args
        )
        for paramType in invoked_method.getGenericParameterTypes()
    ]
    resolved_return_type = resolve_functional_Interface_method_type(
        invoked_method.getGenericReturnType(), j_class_type_parameters, type_args
    )
    return [TypeStr("", resolved_param_types), resolved_return_type]


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
        else:
            union.append(TypeStr(primitive.python_type))

        if is_argument:
            # implicit conversions
            union.append(TypeStr(primitive.python_primitive))
            union.append(TypeStr(primitive.java_object))

    if type_name == "java.lang.String":
        if is_array_param:
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


def translate_java_array_type(
    java_type: Any, type_vars: list[TypeVarStr] | None, is_argument: bool
) -> TypeStr:
    """
    Translate a Java array type to python type.
    """
    element_type = java_array_component_type(java_type)
    python_element_type = python_type(element_type, type_vars, is_array_param=True)

    if python_element_type.name in PARAMETER_TO_ARRAY_TYPE_MAP:
        return TypeStr(PARAMETER_TO_ARRAY_TYPE_MAP[python_element_type.name])
    return TypeStr("java.chaquopy.JavaArray", [python_element_type])


def java_array_component_type(java_type: Any) -> Any:
    """
    Get the component type of a java array type (parametrized type for generic arrays, otherwise "standard" type)
    :param javaType: the array type
    :return: the component type
    """
    from java.lang.reflect import GenericArrayType  # type: ignore

    if isinstance(java_type, GenericArrayType):
        return java_type.getGenericComponentType()
    else:
        return java_type.getComponentType()


def python_type(
    java_type: Any,
    type_vars: list[TypeVarStr] | None = None,
    is_argument: bool = False,
    is_array_param: bool = False,
) -> TypeStr:
    """
    Translate a (possibly generic/parametrized) Java type to a python type, represented as a TypeStr.

    isArgument=True indicates that the type is used as a METHOD ARGUMENT. In this case, JPype applies extra implicit
    type conversions to be handled (see handleImplicitConversions())

    Note that due to the differences of the Java and the python generic typing system, it may not always be possible
    to represent a Java parametrized type fully as a python type. In such case, this method will generate a python
    type which covers the Java type (but may be more permissive than the Java type).

    Java arrays are represented as python Lists, as jpype.JArray is currently not Generic.
    """
    from java.lang.reflect import (  # type: ignore
        GenericArrayType,
        ParameterizedType,
        TypeVariable,
        WildcardType,
    )

    if java_type is None:
        return TypeStr("None")
    if type_vars is None:
        type_vars = []
    if isinstance(java_type, ParameterizedType):
        return translate_type_name(
            str(java_type.getRawType().getTypeName()),
            type_args=[
                python_type(arg, type_vars, is_argument, is_array_param)
                for arg in java_type.getActualTypeArguments()
            ],
            is_argument=is_argument,
            is_array_param=is_array_param,
        )
    elif isinstance(java_type, TypeVariable):
        j_var_name = str(java_type.getName())
        matching_vars = [tv for tv in type_vars if tv.java_name == j_var_name]
        if len(matching_vars) == 1:  # using a known type variable
            return TypeStr(matching_vars[0].python_name)
        else:
            return python_type(java_type_variable_bound(java_type), type_vars)
    elif isinstance(java_type, WildcardType):
        # Java wildcard types, e.g. "? extends Foo". We do not support a feature-complete conversion to the python
        # type system yet, which may anyway not be possible in complex cases with multiple bounds.
        # At the moment we just take the first upper bound, if it is present, otherwise the first lower bound.
        # E.g. "? extends Foo & Bar & Spam" will become "Foo" while "? super
        # Eggs" will become "Eggs"
        j_bound = java_type.getUpperBounds()[0]
        if j_bound.getTypeName() == "java.lang.Object":
            j_lower_bounds = java_type.getLowerBounds()
            if j_lower_bounds:
                j_bound = j_lower_bounds[0]
        return python_type(j_bound, type_vars)
    elif isinstance(java_type, GenericArrayType) or java_type.isArray():
        return translate_java_array_type(java_type, type_vars, is_argument=is_argument)
    else:
        return translate_type_name(
            str(java_type.getName()),
            is_argument=is_argument,
            is_array_param=is_array_param,
        )


def python_type_var(java_type: Any, uniq_scope_id: str) -> TypeVarStr:
    """
    Generate python TypeVar definitions for the provided parametrized Java type. This is complicated by the fact that
    in Java, type variables are defined implictly on the fly, while in python they must be pre-defined (TypeVar). Also,
    type variable bounds are defined inline in Java when USING type variables, while in python they must be defined
    when DECLARING TypeVars.

    To avoid name clashes, the python TypeVars are prefixed with an unique identifier of the scope.

    For example, the Java class definition
    ```
    class EnumMap<K extends Enum, V> extends ...
    ```
    becomes
    ```
    _EnumMap__K = typing.TypeVar('_EnumMap__K', bound=java.lang.Enum)  # <K>
    _EnumMap__V = typing.TypeVar('_EnumMap__V')  # <V>
    class EnumMap(...., typing.Generic[_EnumMap__K, _EnumMap__V]):
    ```

    Note that due to the differences of the Java and the python generic typing system, it may not always be possible
    to represent a Java parametrized type fully as a TypeVar. In such case, this method will generate a python
    TypeVar which covers the Java type (but may be more permissive than the Java type).
    """
    from java.lang.reflect import TypeVariable  # type: ignore

    if not isinstance(java_type, TypeVariable):
        raise RuntimeError(
            f"Can not convert to type var {str(java_type)} ({repr(java_type)})"
        )
    bound: TypeStr | None = python_type(java_type_variable_bound(java_type))
    if bound and bound.name == "java.lang.Object":
        bound = None
    java_name = str(java_type.getName())
    return TypeVarStr(
        java_name=java_name, python_name=f"_{uniq_scope_id}__{java_name}", bound=bound
    )


def java_type_variable_bound(java_type: Any) -> Any:
    """
    Get the bound to use for a particular Java type variable or parametrized type.

    Java type variables and wildcard types can have multiple bounds, e.g. "? extends Foo & Bar & Eggs".
    The python type system can not represent this situation, so for now we just pick the first bound.

    Also, java type bounds can be nested, e.g. "E extends Enum<E>". This is not supported by stubgenj at the
    moment. We generate "E" with a bound of "Enum" in this case.
    """
    from java.lang.reflect import ParameterizedType  # type: ignore

    j_bound = java_type.getBounds()[0]
    if isinstance(j_bound, ParameterizedType):
        j_bound = j_bound.getRawType()
    return j_bound


def infer_arg_name(java_type: Any, prev_args: list[ArgSig]) -> str:
    """
    Infer a 'reasonable' name for function arguments, based on the type of the argument.
    The names are derived from the argument types, by de-capitalizing their (local) names e.g.
       def findParameters(self, parametersRequest: cern.lsa.domain.settings.ParametersRequest)
    If a method takes multiple arguments of the same type, we add "2", "3", ... starting from the second one:
       def updateElementName(self, string: str, string2: str)
    If an argument is a Java array, we add "Array" to the base type name:
       def insertMeasuredTwiss(self, measuredTwissArray: typing.list[cern.lsa.domain.optics.MeasuredTwiss])
    If all else fails, we call the arguments "arg0", "arg1", ...

    Note that if the java class file contains parameter name information, it will be used instead of the
    guess provided by this function. This is an optional Java feature that has to be enabled at build time.
    """
    if java_type is None:
        return f"arg{len(prev_args)}"

    typename = str(java_type.getTypeName())
    is_array = typename.endswith("[]")
    typename = typename.split("<")[0].split("$")[-1].split(".")[-1].replace("[]", "")
    typename = typename[:1].lower() + typename[1:]
    if is_array:
        typename += "Array"
    prev_args_of_type = sum(
        [bool(re.match(typename + r"\d*", prev.name)) for prev in prev_args]
    )
    if prev_args_of_type == 0:
        return typename
    else:
        return typename + str(prev_args_of_type + 1)


def is_static(member: Any) -> bool:
    """Check if a Java class member is static (class function, field, ...)."""
    from java.lang.reflect import Modifier  # type: ignore

    return member.getModifiers() & Modifier.STATIC > 0


def is_public(member: Any) -> bool:
    """Check if a Java class member is public."""
    from java.lang.reflect import Modifier  # type: ignore

    return member.getModifiers() & Modifier.PUBLIC > 0


def is_abstract(member: Any) -> bool:
    """Check if a Java class member is public."""
    from java.lang.reflect import Modifier  # type: ignore

    return member.getModifiers() & Modifier.ABSTRACT > 0


def split_method_overload_javadoc(
    signatures: list[JavaFunctionSig], javadoc: str
) -> list[str]:
    """Split Javadoc by overload signature. The returned list has the same indices as the `signatures` list."""
    IDENTIFIER_REGEX = r"[a-zA-Z0-9_?]+"
    TYPE_REGEX = r"[a-zA-Z0-9_?.,:`~\s]+(<[a-zA-Z0-9_?.,:~\s<>\[\]/=-]+>)?`?(\[\])*\s?"
    GENERIC_ARG_REGEX = (
        rf"[a-zA-Z0-9_?]+( (super {TYPE_REGEX})| (extends {TYPE_REGEX}))?"
    )
    ARG_SEPARATOR = r",\s?"
    signature_regex_list = []

    for signature in signatures:
        # Create a regex that matches signature
        # (we unescape html escapes &lt; &gt; &nbsp; to <, >, " " to make the regex easier to read
        # The start of the signature: modifiers (access, default, abstract,
        # etc.)
        signature_regex = r"(default\s)?(public|protected|private)?\s?"

        # Add static if this signature for a static method
        if signature.static:
            signature_regex += r"static\s"

        # If there type variables, add a regex that can match <A, B, C extends SomeClass>
        # (where the number of type variables is fixed to the number in the signature)
        if len(signature.type_vars) > 0:
            signature_regex += f"<{
                ARG_SEPARATOR.join([GENERIC_ARG_REGEX] * len(signature.type_vars))
            }>\\s"

        # Next is the return type of the method, which is extremely hard to unify exactly due to html links,
        # typing.Union sometimes being used, etc. so make it match any type
        signature_regex += TYPE_REGEX

        # Next is the signature name
        signature_regex += r"\s?" + signature.name

        # Skip the self argument
        args = signature.args
        if len(args) > 0 and args[0].arg_type is None:
            args = args[1:]

        # Create a regex that matches (int arg, SomeClass arg2, int[] arrayArg)
        # (where the number of arguments is fixed to the number in the signature
        signature_regex += (
            r"\s?\("
            + ARG_SEPARATOR.join([TYPE_REGEX + " " + IDENTIFIER_REGEX] * len(args))
            + r"\)"
        )
        signature_regex_list.append(re.compile(signature_regex))
    javadoc_lines = javadoc.split("\n")
    line = 0
    signature_index = None
    out_lines: list[list[str]] = [[] for _ in signatures]

    while line < len(javadoc_lines):
        javadoc_line = javadoc_lines[line]
        for i, regex in enumerate(signature_regex_list):
            # check if the current line matches the signature for any overloads
            match = re.fullmatch(regex, javadoc_line)
            if match is not None:
                # it matches, so skip to next line and set the signature
                # the javadoc is for to i
                signature_index = i
                line = line + 2
                break
        if signature_index is not None and line < len(javadoc_lines):
            # add the line to the current overload javadoc
            out_lines[signature_index].append(javadoc_lines[line])
        line = line + 1
    return ["\n".join(lines) for lines in out_lines]


def generate_java_method_stub(
    parent_name: str,
    name: str,
    j_overloads: list[Any],
    javadoc: dict[str, str],
    classes_done: set[str],
    classes_used: set[str],
    class_type_vars: list[TypeVarStr],
    output: list[str],
    imports_output: list[str],
) -> None:
    """Generate stubs for a single Java method (including the constructor which becomes __init__)."""
    is_constructor = name == "__init__"
    is_overloaded = len(j_overloads) > 1
    signatures: list[JavaFunctionSig] = []
    for i, j_overload in enumerate(sorted(list(j_overloads), key=str)):
        j_return_type = None if is_constructor else j_overload.getGenericReturnType()
        j_args = j_overload.getParameters()
        static = False if is_constructor else is_static(j_overload)
        method_type_vars = [
            python_type_var(
                jType, uniq_scope_id=f"{name}_{i}" if is_overloaded else name
            )
            for jType in j_overload.getTypeParameters()
        ]
        usable_type_vars = (
            method_type_vars + class_type_vars if not static else method_type_vars
        )
        args: list[ArgSig] = [] if static else [ArgSig(name="self")]
        for j_arg in j_args:
            j_arg_type = j_arg.getParameterizedType()
            if j_arg.isVarArgs():
                j_arg_type = java_array_component_type(j_arg_type)
            j_arg_name = (
                str(j_arg.getName())
                if j_arg.isNamePresent()
                else infer_arg_name(j_arg_type, args)
            )
            args.append(
                ArgSig(
                    name=j_arg_name,
                    arg_type=python_type(
                        j_arg_type, usable_type_vars, is_argument=True
                    ),
                    var_args=j_arg.isVarArgs(),
                )
            )

        signatures.append(
            JavaFunctionSig(
                name,
                args=args,
                ret_type=python_type(j_return_type, usable_type_vars),
                static=static,
                type_vars=method_type_vars,
            )
        )

    # in case of overloaded methods, no type var declarations are allowed in
    # between overloads - so put them first.
    for signature in signatures:
        for typeVar in signature.type_vars:
            output.append(
                to_type_var_declaration(
                    typeVar, parent_name, classes_done, classes_used, imports_output
                )
            )

    if javadoc.get(name):
        overloads_javadoc = split_method_overload_javadoc(signatures, javadoc[name])
    else:
        overloads_javadoc = ["" for _ in signatures]

    for signature, overload_javadoc in zip(signatures, overloads_javadoc):
        if is_overloaded:
            imports_output.append("import typing")
            output.append("@typing.overload")
        if signature.static:
            output.append("@staticmethod")
        sig: list[str] = []
        for i, arg in enumerate(signature.args):
            arg_def: str | None
            if arg.name == "self":
                arg_def = arg.name
            else:
                arg_def = pysafe(arg.name)
                if arg_def is None:
                    arg_def = f"invalidArgName{i}"
                if arg.var_args:
                    arg_def = "*" + arg_def

                if arg.arg_type:
                    arg_def += ": " + to_annotated_type(
                        arg.arg_type,
                        parent_name,
                        classes_done,
                        classes_used,
                        imports_output,
                    )

            sig.append(arg_def)

        if is_constructor:
            output.append(
                "def __init__({args}) -> None:{ellipsis}".format(
                    args=", ".join(sig), ellipsis="" if overload_javadoc else " ..."
                )
            )
            if overload_javadoc:
                output.extend(to_docstring_lines(overload_javadoc))
                output.append("    ...")
        else:
            function_name = pysafe(signature.name)
            if function_name is None:
                continue
            # In the future, we should prevent keyword arguments from being
            # used (PEP-570) but that requires 3.8+
            output.append(
                "def {function}({args}) -> {ret}:{ellipsis}".format(
                    function=function_name,
                    args=", ".join(sig),
                    ret=to_annotated_type(
                        signature.ret_type,
                        parent_name,
                        classes_done,
                        classes_used,
                        imports_output,
                    ),
                    ellipsis="" if overload_javadoc else " ...",
                )
            )
            if overload_javadoc:
                output.extend(to_docstring_lines(overload_javadoc))
                output.append("    ...")


def generate_java_field_stub(
    parent_name: str,
    j_field: Any,
    javadoc: dict[str, str],
    classes_done: set[str],
    classes_used: set[str],
    class_type_vars: list[TypeVarStr],
    output: list[str],
    imports_output: list[str],
) -> None:
    """Generate stubs for a single Java class field or constant."""
    if not is_public(j_field):
        return
    static = is_static(j_field)
    field_name = str(j_field.getName())
    field_type = python_type(j_field.getType(), class_type_vars if not static else None)
    field_type_annotation = to_annotated_type(
        field_type,
        parent_name,
        classes_done,
        classes_used,
        imports_output,
        can_be_deferred=True,
    )
    if static:
        imports_output.append("import typing")
        field_type_annotation = f"typing.ClassVar[{field_type_annotation}]"
    py_safe_field_name = pysafe(field_name)
    if py_safe_field_name is None:
        return
    output.append(f"{py_safe_field_name}: {field_type_annotation} = ...")
    if field_name in javadoc:
        output.extend(to_docstring_lines(javadoc[field_name], indent=False))


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
    """
    a_type = type_name.name
    if "." in a_type:
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
        return f"{a_type}[{', '.join(type_args)}]"
    else:
        return a_type


def to_type_var_declaration(
    type_var: TypeVarStr,
    parent_name: str,
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
                    parent_name,
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


def chaquopy_customizer_super_types(
    j_class: jpype.JClass,
    class_type_vars: list[TypeVarStr],
    customizers_used: set[type],
    imports_output: list[str],
) -> list[str]:
    """Get extra 'artificial' super types to add, to take into account the effect of JPype customizers."""
    extra_super_types = []
    # for customizer in j_class._hints.implementations:
    #     type_str = customizer.__qualname__
    #     if class_type_vars:
    #         type_str += (
    #             "[" + ", ".join([tv.python_name for tv in class_type_vars]) + "]"
    #         )
    #     extra_super_types.append(type_str)
    #     customizers_used.add(customizer)
    if j_class.class_.getName() == "java.lang.Throwable":
        # Workaround to allow Throwable-derived exception types be recognized
        # as JException, so that they can be assigned as Exception.__cause__
        extra_super_types.append("builtins.Exception")
        imports_output.append("import builtins")
    return extra_super_types
    return []


def sanitize_javadoc_html(escaped_html: str | None) -> str:
    """Un-Escape common html escapes used, and change the non-breaking space (unicode 200B) to ' '"""
    if escaped_html is None:
        return ""
    else:
        return (
            str(escaped_html)
            .replace("\u200b", " ")
            .replace("\xa0", " ")
            .replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )


def extract_class_javadoc(j_class: jpype.JClass) -> Javadoc:
    try:
        from org.jpype.javadoc import JavadocExtractor  # type: ignore

        j_doc = JavadocExtractor().getDocumentation(j_class)
        if j_doc is None:
            return Javadoc(description="")
        else:
            return Javadoc(
                description=sanitize_javadoc_html(j_doc.description).strip(),
                ctors=sanitize_javadoc_html(j_doc.ctors),
                methods={
                    name: sanitize_javadoc_html(doc)
                    for name, doc in j_doc.methods.items()
                },
                fields={
                    name: sanitize_javadoc_html(doc)
                    for name, doc in j_doc.fields.items()
                },
            )
    except (jpype.JException, ImportError):
        return Javadoc(description="")


def to_docstring_lines(doc: str, indent: bool = True) -> list[str]:
    if not doc:
        return []
    indent_str = "    " if indent else ""
    javadoc_output = [indent_str + javadoc_line for javadoc_line in doc.split("\n")]
    return [f'{indent_str}"""'] + javadoc_output + [f'{indent_str}"""']


def generate_java_class_stub(
    package: jpype.JPackage,
    j_class: jpype.JClass,
    include_javadoc: bool,
    classes_done: set[str],
    classes_used: set[str],
    customizers_used: set[type],
    output: list[str],
    imports_output: list[str],
    type_var_output: list[str] | None = None,
    parent_class_type_vars: list[TypeVarStr] | None = None,
) -> None:
    """Generate stubs for a single Java class and all of it's nested classes."""
    package_name = package.__name__
    items = sorted(vars(j_class).items(), key=lambda x: x[0])

    if include_javadoc:
        javadoc = extract_class_javadoc(j_class)
    else:
        javadoc = Javadoc(description="")

    write_type_vars_to_output = False
    if type_var_output is None:
        write_type_vars_to_output = True
        type_var_output = []

    class_prefix = (
        str(j_class.class_.getName())
        .replace(package_name + ".", "")
        .replace(".", "_")
        .replace("$", "__")
    )
    class_type_vars = [
        python_type_var(t, uniq_scope_id=class_prefix)
        for t in j_class.class_.getTypeParameters()
    ]
    if parent_class_type_vars is None or is_static(j_class.class_):
        usable_type_vars = class_type_vars
    else:
        usable_type_vars = parent_class_type_vars + class_type_vars

    constructors_output: list[str] = []
    constructors = j_class.class_.getConstructors()
    generate_java_method_stub(
        package_name,
        "__init__",
        constructors,
        {"__init__": javadoc.ctors},
        classes_done=classes_done,
        classes_used=classes_used,
        class_type_vars=usable_type_vars,
        output=constructors_output,
        imports_output=imports_output,
    )

    methods_output: list[str] = []
    j_overloads = j_class.class_.getMethods()
    for attr, value in items:
        if isinstance(value, jpype.JMethod):
            matching_overloads = [
                o
                for o in j_overloads
                if pysafe(str(o.getName())) == attr and not o.isSynthetic()
            ]
            generate_java_method_stub(
                package_name,
                attr,
                matching_overloads,
                javadoc.methods,
                classes_done=classes_done,
                classes_used=classes_used,
                class_type_vars=usable_type_vars,
                output=methods_output,
                imports_output=imports_output,
            )

    fields_output: list[str] = []
    j_fields = j_class.class_.getDeclaredFields()
    for j_field in j_fields:
        generate_java_field_stub(
            package_name,
            j_field,
            javadoc.fields,
            classes_done=classes_done,
            classes_used=classes_used,
            class_type_vars=usable_type_vars,
            output=fields_output,
            imports_output=imports_output,
        )

    nested_classes_output: list[str] = []
    classes_done_nested: set[str] = set()
    for attr, value in items:
        if is_java_class(value):
            nested_done = set(classes_done)
            generate_java_class_stub(
                package,
                value,
                include_javadoc,
                nested_done,
                classes_used,
                customizers_used,
                output=nested_classes_output,
                type_var_output=type_var_output,
                imports_output=imports_output,
                parent_class_type_vars=usable_type_vars,
            )
            classes_done_nested |= nested_done

    while True:
        nested_classes_used = {
            t.split(".")[-1]
            for t in classes_used
            if t.startswith(str(j_class.class_.getName()) + "$")
        }
        remaining_private_nested_classes = nested_classes_used - (
            classes_done | classes_done_nested
        )
        if not remaining_private_nested_classes:
            break
        for nested_class in sorted(remaining_private_nested_classes):
            cls = None
            try:
                cls = getattr(j_class, nested_class.split("$")[1])
            except (ImportError, AttributeError):
                pass
            if cls is not None:
                nested_done = set(classes_done)
                generate_java_class_stub(
                    package,
                    cls,
                    include_javadoc,
                    nested_done,
                    classes_used,
                    customizers_used,
                    output=nested_classes_output,
                    type_var_output=type_var_output,
                    imports_output=imports_output,
                    parent_class_type_vars=usable_type_vars,
                )
                classes_done_nested |= nested_done
            else:
                log.warning(
                    f"reference to missing inner class {nested_class} - generating empty stub"
                )
                generate_empty_class_stub(
                    nested_class,
                    classes_done=classes_done_nested,
                    output=nested_classes_output,
                )

    super_types = []
    for super_type in java_super_types(j_class):
        super_types.append(
            to_annotated_type(
                python_type(super_type, usable_type_vars),
                package_name,
                classes_done,
                classes_used,
                imports_output,
                can_be_deferred=False,
            )
        )
    if class_type_vars:
        generic_type_arguments = ", ".join([tv.python_name for tv in class_type_vars])
        super_types.append(f"typing.Generic[{generic_type_arguments}]")
    super_types = super_types + chaquopy_customizer_super_types(
        j_class, class_type_vars, customizers_used, imports_output
    )
    for type_var in class_type_vars:
        type_var_output.append(
            to_type_var_declaration(
                type_var, package_name, classes_done, classes_used, imports_output
            )
        )

    super_type_str = f"({', '.join(super_types)})" if super_types else ""

    class_name = str(
        j_class.class_.getSimpleName()
    )  # do not use python_typename to avoid mangling classes

    if write_type_vars_to_output:
        output.append("")
        output += type_var_output

    javadoc_output = to_docstring_lines(javadoc.description)

    if (
        not constructors_output
        and not methods_output
        and not fields_output
        and not nested_classes_output
    ):
        if javadoc_output:
            output.append(f"class {class_name}{super_type_str}:")
            output.extend(javadoc_output)
            output.append("    ...")
        else:
            output.append(f"class {class_name}{super_type_str}: ...")
    else:
        output.append(f"class {class_name}{super_type_str}:")
        output.extend(javadoc_output)
        for line in fields_output:
            output.append(f"    {line}")
        for line in constructors_output:
            output.append(f"    {line}")
        for line in methods_output:
            output.append(f"    {line}")
        for line in nested_classes_output:
            output.append(f"    {line}")
    classes_done |= classes_done_nested
    classes_done.add(simple_class_name_of(j_class))


def generate_empty_class_stub(
    class_name: str, classes_done: set[str], output: list[str]
):
    """Generate an empty class stub. This is used to represent classes with are not accessible (e.g. private)"""
    classes_done.add(class_name)
    local_class_name = class_name.split("$")[
        -1
    ]  # in case the class is an nested class ("Class$NestedClass") ...
    output.append(f"class {local_class_name}: ...")
