import logging
import tempfile

import mypy.build
import mypy.modulefinder
import mypy.test.testcheck
import pytest

import chaquopy_stubgen
from pathlib import Path
from typing import Generator


@pytest.fixture(scope="session", autouse=True)
def stub_tmpdir() -> Generator[str, None, None]:
    logging.basicConfig(level="INFO")
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(scope="session", autouse=True)
def setup_mypy_for_data_driven_tests(stub_tmpdir: str):
    _real_build = mypy.build.build

    def _patched_build(sources, options, *args, **kwargs):
        options.use_builtins_fixtures = False
        return _real_build(sources, options, *args, **kwargs)

    mypy.build.build = _patched_build

    mypy.modulefinder.get_search_dirs = lambda _: ([stub_tmpdir], [stub_tmpdir])  # type: ignore


def test_generate_stubs(stub_tmpdir: Path):
    import java  # type: ignore

    chaquopy_stubgen.generate_java_stubs(
        [java],  # type: ignore
        output_dir=stub_tmpdir,
    )


@pytest.mark.trylast
class StubTestSuite(mypy.test.testcheck.TypeCheckSuite):
    def setup(self) -> None:
        pass


    files = [
        "arraylist.test",
        "callbacks.test",
        "enummap.test",
        "forward_declaration.test",
        "hashmap.test",
        "mangled_python_keywords.test",
        "varargs.test",
        "exception.test",
        "type_conversions.test",
        "jarray.test"
    ]
