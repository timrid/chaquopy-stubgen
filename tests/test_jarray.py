from .conftest import run_mypy
from pathlib import Path


def test_java_array_as_return_type(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import String

s = String("asdf")
reveal_type(s)
reveal_type(s.split("s"))
reveal_type(s.toCharArray())
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:4: note: Revealed type is "java.lang.String"
testfile.py:5: note: Revealed type is "java.chaquopy.JavaArray[java.lang.String]"
testfile.py:6: note: Revealed type is "java.chaquopy.JavaArrayJChar"
Success: no issues found in 1 source file
""",
    )


def test_java_array_as_parameter(stub_dir: Path, mypy_project_dir: Path):
    code = """\
from java.lang import String
from java import jarray, jchar, jint, jbyte

char_array = jarray(jchar)(["a", "b", "c"])
byte_array = jarray(jbyte)([55, 66, 77])
int_array = jarray(jint)([55555, 66, 77])
reveal_type(char_array)
reveal_type(byte_array)
reveal_type(int_array)
String(char_array)
String(byte_array)
String(int_array)
"""

    run_mypy(
        mypy_project_dir,
        stub_dir,
        code,
        expected_stdout="""\
testfile.py:7: note: Revealed type is "java.chaquopy.JavaArrayJChar"
testfile.py:8: note: Revealed type is "java.chaquopy.JavaArrayJByte"
testfile.py:9: note: Revealed type is "java.chaquopy.JavaArrayJInt"
testfile.py:12: error: No overload variant of "String" matches argument type "JavaArrayJInt"  [call-overload]
testfile.py:12: note: Possible overload variants:
testfile.py:12: note:     def String(self) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, int: int | jint | Integer) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, int: int | jint | Integer, int2: int | jint | Integer) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, int: int | jint | Integer, int2: int | jint | Integer, int3: int | jint | Integer) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, int: int | jint | Integer, int2: int | jint | Integer, string: str | String) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, int: int | jint | Integer, int2: int | jint | Integer, charset: Charset) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, string: str | String) -> String
testfile.py:12: note:     def String(self, byteArray: JavaArrayJByte, charset: Charset) -> String
testfile.py:12: note:     def String(self, charArray: JavaArrayJChar) -> String
testfile.py:12: note:     def String(self, charArray: JavaArrayJChar, int: int | jint | Integer, int2: int | jint | Integer) -> String
testfile.py:12: note:     def String(self, intArray: JavaArrayJInt, int2: int | jint | Integer, int3: int | jint | Integer) -> String
testfile.py:12: note:     def String(self, string: str | String) -> String
testfile.py:12: note:     def String(self, stringBuffer: StringBuffer) -> String
testfile.py:12: note:     def String(self, stringBuilder: StringBuilder) -> String
Found 1 error in 1 file (checked 1 source file)
""",
        expected_returncode=1,
    )
