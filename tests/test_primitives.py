from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_primitives(mypy_project_dir: Path):
    code = """\
from java import jboolean, jbyte, jshort, jint, jlong, jfloat, jdouble, jchar

val_bool = jboolean(True)
val_byte = jbyte(127)
val_short = jshort(32767)
val_int = jint(42)
val_long = jlong(9223372036854775807)
val_float = jfloat(3.14)
val_double = jdouble(3.141592653589793)
val_char = jchar("x")

reveal_type(val_bool)  # *10
reveal_type(val_bool.value)  # *11
reveal_type(val_byte)  # *20
reveal_type(val_byte.value)  # *21
reveal_type(val_short)  # *30
reveal_type(val_short.value)  # *31
reveal_type(val_int)  # *40
reveal_type(val_int.value)  # *41
reveal_type(val_long)  # *50
reveal_type(val_long.value)  # *51
reveal_type(val_float)  # *60
reveal_type(val_float.value)  # *61
reveal_type(val_double)  # *70
reveal_type(val_double.value)  # *71
reveal_type(val_char)  # *80
reveal_type(val_char.value)  # *81
"""

    expected_mypy_output = {
        "*10": 'note: Revealed type is "java.primitive.jboolean"',
        "*11": 'note: Revealed type is "builtins.bool"',
        "*20": 'note: Revealed type is "java.primitive.jbyte"',
        "*21": 'note: Revealed type is "builtins.int"',
        "*30": 'note: Revealed type is "java.primitive.jshort"',
        "*31": 'note: Revealed type is "builtins.int"',
        "*40": 'note: Revealed type is "java.primitive.jint"',
        "*41": 'note: Revealed type is "builtins.int"',
        "*50": 'note: Revealed type is "java.primitive.jlong"',
        "*51": 'note: Revealed type is "builtins.int"',
        "*60": 'note: Revealed type is "java.primitive.jfloat"',
        "*61": 'note: Revealed type is "builtins.float"',
        "*70": 'note: Revealed type is "java.primitive.jdouble"',
        "*71": 'note: Revealed type is "builtins.float"',
        "*80": 'note: Revealed type is "java.primitive.jchar"',
        "*81": 'note: Revealed type is "builtins.str"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_primitives_with_truncate(mypy_project_dir: Path):
    code = """\
from java import jbyte, jshort, jint, jlong, jfloat, jdouble

val_byte = jbyte(256, truncate=True)
val_short = jshort(32768, truncate=True)
val_int = jint(2147483648, truncate=True)
val_long = jlong(9223372036854775808, truncate=True)
val_float = jfloat(3.4e39, truncate=True)
val_double = jdouble(1.8e309, truncate=True)

reveal_type(val_byte)  # *1
reveal_type(val_short)  # *2
reveal_type(val_int)  # *3
reveal_type(val_long)  # *4
reveal_type(val_float)  # *5
reveal_type(val_double)  # *6
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.primitive.jbyte"',
        "*2": 'note: Revealed type is "java.primitive.jshort"',
        "*3": 'note: Revealed type is "java.primitive.jint"',
        "*4": 'note: Revealed type is "java.primitive.jlong"',
        "*5": 'note: Revealed type is "java.primitive.jfloat"',
        "*6": 'note: Revealed type is "java.primitive.jdouble"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_primitive_overload_resolution(mypy_project_dir: Path):
    code = """\
from java import jint
from java.io import PrintStream

p = PrintStream("test.txt")
reveal_type(p.print_)  # *1
"""

    expected_mypy_output = {
        "*1": (
            'note: Revealed type is "Overload'
            '(def (builtins.str | java.primitive.jchar | java.lang.Character), '
            'def (builtins.float | java.primitive.jdouble | java.lang.Double), '
            'def (builtins.float | java.primitive.jfloat | java.lang.Float), '
            'def (builtins.int | java.primitive.jint | java.lang.Integer), '
            'def (builtins.int | java.primitive.jlong | java.lang.Long), '
            'def (java.lang.Object | builtins.int | builtins.bool | builtins.float | builtins.str), '
            'def (builtins.str | java.lang.String), def (builtins.bool | java.primitive.jboolean | java.lang.Boolean), '
            'def (java.chaquopy.JavaArrayJChar))"'
        )
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)
