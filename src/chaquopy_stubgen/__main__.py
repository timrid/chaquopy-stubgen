import argparse
import logging
import time
from pathlib import Path

from chaquopy_stubgen.stubgen import convert_jar_to_python_stubs

log = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    parser = argparse.ArgumentParser(
        description="Generate Python Type Stubs for Java classes that are optimized for chaquopy."
    )
    parser.add_argument(
        "jars",
        type=str,
        nargs="+",
        help="List of .jar or .aar files to include in the classpath.",
    )
    parser.add_argument(
        "--jvmpath",
        type=str,
        help='path to the JVM ("libjvm.so", "jvm.dll", ...) (default: use system default JVM)',
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./dist/stubs",
        help="path to write stubs to (default: .)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    jars = [Path(jar) for jar in args.jars]
    if len(args.jars) == 0:
        log.error("No JAR files provided.")
        exit(1)
    elif len(args.jars) > 1:
        log.error("Multiple JAR files currently not supported.")
        exit(1)

    log.info(f"Generating stubs for {jars[0]} to {output_dir}")
    t0 = time.perf_counter()
    convert_jar_to_python_stubs(jars[0], output_dir, jvmpath=args.jvmpath)
    elapsed = time.perf_counter() - t0
    log.info(f"Generation done in {elapsed:.1f}s.")
