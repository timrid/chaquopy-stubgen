# Note that this conftest file exists at the package level as it is needed to configure
# the JVM for docstrings at the package level.
from collections.abc import Generator
from contextlib import contextmanager
import os
from pathlib import Path
import logging
import tempfile
import textwrap
import mypy.api
import pytest

import chaquopy_stubgen

logger = logging.getLogger(__name__)


ANDROID_JAR = Path(__file__).parent / "android-35.jar"


@pytest.fixture(scope="session")
def jvm():
    import jpype  # type: ignore

    if not jpype.isJVMStarted():
        jpype.startJVM(None, classpath=[ANDROID_JAR], convertStrings=True)  # type: ignore
    import jpype.imports  # type: ignore

    yield jpype

@pytest.fixture(scope="session")
def stub_dir(jvm) -> Generator[Path, None, None]:
    # logging.basicConfig(level="DEBUG")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        import java  # type: ignore

        logger.debug(f"Generating stubs in {tmpdir}...")

        chaquopy_stubgen.generate_java_stubs(
            [java],  # type: ignore
            output_dir=tmpdir,
        )

        # Rename "java-stubs" to "java"
        (tmpdir / "java-stubs").rename(tmpdir / "java")

        yield tmpdir


@contextmanager
def change_dir(path: Path) -> Generator[None, None, None]:
    old = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)

@pytest.fixture(scope="session")
def mypy_project_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

def run_mypy(
    project_dir: Path,
    extra_stub: Path,
    test_code: str,
    expected_stdout: str,
    expected_stderr: str = "",
    expected_returncode: int = 0,
) -> tuple[str, str, int]:
    with change_dir(project_dir):
        with project_dir.joinpath("pyproject.toml").open("w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [tool.mypy]
                    mypy_path = "{extra_stub.absolute()}"

                    [[tool.mypy.overrides]]
                    module = "java.*"
                    ignore_errors = true
                    """
                )
            )

        testfile_name = "testfile.py"
        with project_dir.joinpath(testfile_name).open("w") as f:
            f.write(test_code)

        result = mypy.api.run([testfile_name])

        mypy_stdout, mypy_stderr, mypy_returncode = result
        logger.debug(f"mypy stdout: {mypy_stdout}")
        logger.debug(f"mypy stderr: {mypy_stderr}")
        logger.debug(f"mypy returncode: {mypy_returncode}")

        assert mypy_stdout.strip() == expected_stdout.strip()
        assert mypy_stderr.strip() == expected_stderr.strip()
        assert mypy_returncode == expected_returncode
    return result