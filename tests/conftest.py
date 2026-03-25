# Note that this conftest file exists at the package level as it is needed to configure
# the JVM for docstrings at the package level.
import logging
import tempfile
import textwrap
from collections.abc import Generator
from pathlib import Path

import pytest

import chaquopy_stubgen

logger = logging.getLogger(__name__)


ANDROID_JAR = Path(__file__).parent / "android-35.jar"
KOTLIN_STDLIB_JAR = Path(__file__).parent / "kotlin-stdlib-2.3.20.jar"


@pytest.fixture(scope="session")
def stub_dir() -> Generator[Path, None, None]:
    # logging.basicConfig(level="DEBUG")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        logger.debug(f"Generating stubs in {tmpdir}...")

        chaquopy_stubgen.convert_to_python_stubs(
            [ANDROID_JAR, KOTLIN_STDLIB_JAR], tmpdir
        )

        # # Rename "java-stubs" to "java"
        # (tmpdir / "java-stubs").rename(tmpdir / "java")

        yield tmpdir


@pytest.fixture(scope="session")
def mypy_project_dir(stub_dir: Path) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        with project_dir.joinpath("pyproject.toml").open("w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [tool.mypy]
                    mypy_path = "{stub_dir.absolute()}"

                    [[tool.mypy.overrides]]
                    module = "java.*"
                    ignore_errors = true
                    """
                )
            )
        yield project_dir
