"""
ASM-based Java stub generator.

Generates Python type stubs from Java .class files using the ASM bytecode library,
without requiring a running JVM with the target classes loaded (only ASM itself is needed).
"""

from __future__ import annotations

import concurrent.futures
import logging
import multiprocessing
import shutil
import zipfile
from pathlib import Path

from chaquopy_stubgen._class_stub import convert_java_class_to_python_stub
from chaquopy_stubgen.chaquopy_bindings import add_chaquopy_bindings_to_java_package


log = logging.getLogger(__name__)

DEFAULT_CLASSPATH = ["asm-9.6.jar", "asm-tree-9.6.jar"]


def _worker_init(jvmpath: str | None, log_level: int) -> None:
    """Start a JVM in this worker process and register shutdown via atexit."""
    import atexit

    import jpype  # type: ignore
    import jpype.imports  # type: ignore

    logging.basicConfig(level=log_level)
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
        for imp in sorted(combined_imports):
            f.write(imp + "\n")
        f.write("\n\n")
        for line in combined_code:
            f.write(line + "\n")

    elapsed = time.perf_counter() - t0
    log.info(f"Finished package {package_dir} in {elapsed:.2f}s")


def convert_jar_to_python_stubs(
    jar_file_path: Path, output_dir: Path, jvmpath: str | None = None
) -> None:
    """
    Extract all .class files from the given JAR file and convert them to Python stubs.
    Produces a directory tree with __init__.pyi files.
    """
    if len(output_dir.resolve().parts) < 3:
        raise ValueError(
            f"output_dir '{output_dir}' is dangerously close to the filesystem root, "
            "refusing to delete it."
        )
    shutil.rmtree(output_dir, ignore_errors=True)

    with zipfile.ZipFile(jar_file_path, "r") as jar:
        class_entries = [e for e in jar.namelist() if e.endswith(".class")]

        # Group by package directory and pre-read all class data so workers
        # don't need to access the ZIP concurrently.
        packages: dict[str, list[str]] = {}
        for class_file in class_entries:
            package_dir = str(Path(class_file).parent)
            packages.setdefault(package_dir, []).append(class_file)

        all_class_data: dict[str, dict[str, bytes]] = {
            package_dir: {f.removesuffix(".class"): jar.read(f) for f in class_files}
            for package_dir, class_files in packages.items()
        }

    # Ensure the "java" package is present so that the base chaquopy bindings are generated.
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

