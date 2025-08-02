# Note that this conftest file exists at the package level as it is needed to configure
# the JVM for docstrings at the package level.
import os
import pathlib

import pytest


pytest_plugins = [
    "mypy.test.data",
]
os.environ["MYPY_TEST_PREFIX"] = str(pathlib.Path(__file__).parent / "stubtest")

ANDROID_JAR = pathlib.Path(__file__).parent / "android-35.jar"


@pytest.fixture(autouse=True, scope="session")
def jvm():
    import jpype  # type: ignore

    if not jpype.isJVMStarted():
        jpype.startJVM(None, classpath=[ANDROID_JAR], convertStrings=True)  # type: ignore
    import jpype.imports  # type: ignore

    yield jpype
