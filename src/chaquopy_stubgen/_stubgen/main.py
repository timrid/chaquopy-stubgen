"""
ASM-based Java stub generator.

Generates Python type stubs from Java .class files using the ASM bytecode library,
without requiring a running JVM with the target classes loaded (only ASM itself is needed).
"""

from __future__ import annotations

import concurrent.futures
import io
import logging
import multiprocessing
import shutil
import zipfile
from collections.abc import Iterable
from pathlib import Path

from chaquopy_stubgen._log import configure_logging
from chaquopy_stubgen._stubgen.chaquopy_bindings import (
    add_chaquopy_bindings_to_java_package,
)
from chaquopy_stubgen._stubgen.class_stub import convert_java_class_to_python_stub

log = logging.getLogger(__name__)

_JVM_LIBS_DIR = Path(__file__).parent.parent / "_jvm_libs"
DEFAULT_CLASSPATH = [
    str(_JVM_LIBS_DIR / "asm-9.6.jar"),
    str(_JVM_LIBS_DIR / "asm-tree-9.6.jar"),
]


def _worker_init(jvmpath: str | None, log_level: int) -> None:
    """Start a JVM in this worker process and register shutdown via atexit."""
    import atexit

    import jpype  # type: ignore
    import jpype.imports  # type: ignore

    configure_logging(log_level)
    jpype.startJVM(jvmpath=jvmpath, classpath=DEFAULT_CLASSPATH)
    atexit.register(jpype.shutdownJVM)


def _process_package(
    package_dir: str,
    class_files: list[str],
    package_class_data: dict[str, bytes],
    output_dir: Path,
) -> None:
    """Process one Java package and write its __init__.pyi."""
    import time

    top_level_files = [f for f in class_files if "$" not in Path(f).stem]
    t0 = time.perf_counter()
    log.info(
        f"Processing package {package_dir} "
        f"({len(top_level_files)} top-level / {len(class_files)} total classes)..."
    )

    # Pre-populate with all top-level class names so that intra-package
    # references (e.g., superclass) always use the short name regardless
    # of alphabetical processing order (e.g., D before P).
    classes_done: set[str] = {Path(f).stem for f in top_level_files}
    classes_used: set[str] = set()
    combined_imports: set[str] = set()
    combined_code: list[str] = []

    for class_file in sorted(top_level_files):
        try:
            stub = convert_java_class_to_python_stub(
                class_file,
                package_class_data[class_file.removesuffix(".class")],
                all_class_data=package_class_data,
                classes_done=classes_done,
                classes_used=classes_used,
            )
        except Exception as e:
            log.warning(f"Skipping {class_file}: {e}")
            continue
        combined_imports.update(stub.imports)
        combined_code.extend(stub.type_vars)  # module-level TypeVar declarations
        combined_code.extend(stub.code)  # class definition

    if package_dir == "java":
        add_chaquopy_bindings_to_java_package(
            output_dir / "java", combined_imports, combined_code
        )

    output_file = output_dir / Path(package_dir) / "__init__.pyi"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        # separate standard library imports from generated imports for readability and for isort compatibility
        STD_LIB_IMPORTS = {"import typing", "import builtins"}
        std_lib_imports = combined_imports & STD_LIB_IMPORTS
        for std_imp in sorted(std_lib_imports):
            f.write(std_imp + "\n")
        if len(std_lib_imports) > 0:
            f.write("\n")
        other_imports = combined_imports - STD_LIB_IMPORTS
        for imp in sorted(other_imports):
            f.write(imp + "\n")
        for line in combined_code:
            f.write(line + "\n")

    elapsed = time.perf_counter() - t0
    log.info(f"Finished package {package_dir} in {elapsed:.2f}s")


def _open_jar_or_aar_from_file(file_path: Path) -> zipfile.ZipFile:
    """
    Open a .jar or .aar file and return a ZipFile pointing to the JAR contents.

    For .jar files the archive is opened directly.
    For .aar files ``classes.jar`` is extracted from the archive and wrapped in a
    BytesIO buffer so that the caller gets the same ZipFile interface in both cases.
    Raises ValueError for unsupported file extensions or when no ``classes.jar`` is
    found inside an .aar.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".jar":
        return zipfile.ZipFile(file_path, "r")
    elif suffix == ".aar":
        with zipfile.ZipFile(file_path, "r") as aar:
            aar_entries = aar.namelist()
            if "classes.jar" not in aar_entries:
                raise ValueError(
                    f"No 'classes.jar' found in AAR '{file_path}'. "
                    f"Available entries: {aar_entries}"
                )
            jar_data = aar.read("classes.jar")
        return zipfile.ZipFile(io.BytesIO(jar_data), "r")
    else:
        raise ValueError(
            f"Unsupported file format '{file_path.suffix}'. Expected '.jar' or '.aar'."
        )


def _collect_packages_from_entries(
    entries: Iterable[tuple[str, bytes]],
) -> tuple[dict[str, list[str]], dict[str, dict[str, bytes]]]:
    """
    Group an iterable of ``(relative_class_path, bytecode)`` pairs by their
    parent directory (Java package), returning the two-level structure used
    throughout the stub-generation pipeline.
    """
    packages: dict[str, list[str]] = {}
    class_data: dict[str, dict[str, bytes]] = {}
    for class_file, data in entries:
        package_dir = str(Path(class_file).parent)
        packages.setdefault(package_dir, []).append(class_file)
        class_data.setdefault(package_dir, {})[class_file.removesuffix(".class")] = data
    return packages, class_data


def convert_to_python_stubs(
    input_paths: list[Path],
    output_dir: Path,
    jvmpath: str | None = None,
    clear_output_dir: bool = True,
) -> None:
    """
    Convert one or more .jar/.aar files or directories of .class files to
    Python type stubs.

    Accepts plain ``.jar`` files or Android ``.aar`` archives (whose
    ``classes.jar`` is used), as well as directories that contain ``.class``
    files (searched recursively).  Produces a directory tree of
    ``__init__.pyi`` files under *output_dir*.

    Raises ValueError if the same Java package appears in more than one of the
    provided inputs — all inputs are inspected before any output is written.

    If *clear_output_dir* is ``False`` the output directory is not deleted
    before writing; existing files will be overwritten but unrelated files
    are kept.
    """
    if clear_output_dir and len(output_dir.resolve().parts) < 3:
        raise ValueError(
            f"output_dir '{output_dir}' is dangerously close to the filesystem root, "
            "refusing to delete it."
        )

    # Collect packages and class data from all inputs before touching the output
    # directory so that collision errors are raised without side effects.
    packages: dict[str, list[str]] = {}
    all_class_data: dict[str, dict[str, bytes]] = {}
    for input_path in input_paths:
        suffix = input_path.suffix.lower()
        if suffix in (".jar", ".aar"):
            with _open_jar_or_aar_from_file(input_path) as jar:
                new_packages, new_class_data = _collect_packages_from_entries(
                    (f, jar.read(f)) for f in jar.namelist() if f.endswith(".class")
                )
        else:
            new_packages, new_class_data = _collect_packages_from_entries(
                (f.relative_to(input_path).as_posix(), f.read_bytes())
                for f in sorted(input_path.rglob("*.class"))
            )

        collisions = sorted(set(new_packages) & set(packages))
        if collisions:
            raise ValueError(
                f"Package collision detected when loading '{input_path}': {collisions}"
            )

        for package_dir, class_files in new_packages.items():
            packages[package_dir] = class_files
            all_class_data[package_dir] = new_class_data[package_dir]

    if clear_output_dir:
        shutil.rmtree(output_dir, ignore_errors=True)

    # Only inject the synthetic "java" package (chaquopy bindings) when at least
    # one sub-package of "java" (e.g. "java/lang", "java/util") is present.
    if any(p.startswith("java/") for p in packages):
        packages.setdefault("java", [])
        all_class_data.setdefault("java", {})

    # Each worker process gets its own JVM instance, achieving true parallelism
    # unhindered by the GIL.  All data passed to workers is plain bytes/strings
    # (fully picklable) so spawn-based multiprocessing works fine on macOS.
    # "spawn" is used explicitly (instead of the Linux default "fork") because
    # forking a process with a running JVM causes undefined behaviour in JPype.
    mp_context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        initializer=_worker_init,
        initargs=(jvmpath, log.getEffectiveLevel()),
        mp_context=mp_context,
    ) as pool:
        futures = [
            pool.submit(
                _process_package,
                package_dir,
                class_files,
                all_class_data[package_dir],
                output_dir,
            )
            for package_dir, class_files in packages.items()
        ]
        for future in concurrent.futures.as_completed(futures):
            if exc := future.exception():
                log.error(f"Package processing failed: {exc}")
