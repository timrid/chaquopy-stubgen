from pathlib import Path

from .mypy_helper import run_and_assert_mypy


def test_java_array_as_return_type(mypy_project_dir: Path):
    code = """\
from java.lang import String

s = String("asdf")
reveal_type(s)  # *1
reveal_type(s.split("s"))  # *2
reveal_type(s.toCharArray())  # *3
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.lang.String"',
        "*2": 'note: Revealed type is "java.chaquopy.JavaArray[java.lang.String]"',
        "*3": 'note: Revealed type is "java.chaquopy.JavaArrayJChar"',
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)


def test_java_array_as_parameter(mypy_project_dir: Path):
    code = """\
from java.lang import String
from java import jarray, jchar, jint, jbyte

char_array = jarray(jchar)(["a", "b", "c"])
byte_array = jarray(jbyte)([55, 66, 77])
int_array = jarray(jint)([55555, 66, 77])
reveal_type(char_array)  # *1
reveal_type(byte_array)  # *2
reveal_type(int_array)  # *3
String(char_array)
String(byte_array)
String(int_array)  # *4
"""

    expected_mypy_output = {
        "*1": 'note: Revealed type is "java.chaquopy.JavaArrayJChar"',
        "*2": 'note: Revealed type is "java.chaquopy.JavaArrayJByte"',
        "*3": 'note: Revealed type is "java.chaquopy.JavaArrayJInt"',
        "*4": """\
error: No overload variant of "String" matches argument type "JavaArrayJInt"
hint: Possible overload variants:
hint:     def String(self) -> String
hint:     def String(self, str | String, /) -> String
hint:     def String(self, StringBuffer, /) -> String
hint:     def String(self, StringBuilder, /) -> String
hint:     def String(self, JavaArrayJByte, /) -> String
hint:     def String(self, JavaArrayJChar, /) -> String
hint:     def String(self, JavaArrayJByte, int | jint | Integer, /) -> String
hint:     def String(self, JavaArrayJByte, str | String, /) -> String
hint:     def String(self, JavaArrayJByte, Charset, /) -> String
hint:     def String(self, JavaArrayJByte, int | jint | Integer, int | jint | Integer, /) -> String
hint:     def String(self, JavaArrayJChar, int | jint | Integer, int | jint | Integer, /) -> String
hint:     def String(self, JavaArrayJInt, int | jint | Integer, int | jint | Integer, /) -> String
hint:     def String(self, JavaArrayJByte, int | jint | Integer, int | jint | Integer, int | jint | Integer, /) -> String
hint:     def String(self, JavaArrayJByte, int | jint | Integer, int | jint | Integer, str | String, /) -> String
hint:     def String(self, JavaArrayJByte, int | jint | Integer, int | jint | Integer, Charset, /) -> String"""
    }

    run_and_assert_mypy(mypy_project_dir, code, expected_mypy_output)

    
