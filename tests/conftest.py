# Note that this conftest file exists at the package level as it is needed to configure
# the JVM for docstrings at the package level.
from collections.abc import Generator
from pathlib import Path
import logging
import tempfile
import pytest

import chaquopy_stubgen

logger = logging.getLogger(__name__)


ANDROID_JAR = Path(__file__).parent / "android-35.jar"


@pytest.fixture(scope="session")
def jvm():
    import jpype  # type: ignore

    jpype.startJVM(None, classpath=[ANDROID_JAR], convertStrings=True)  # type: ignore
    import jpype.imports  # type: ignore

    try:
       yield jpype
    finally:
        jpype.shutdownJVM()

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


@pytest.fixture(scope="session")
def mypy_project_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

