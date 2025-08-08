import argparse
import importlib
import logging
from glob import glob

import jpype.imports  # type: ignore

from . import generate_java_stubs

log = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    parser = argparse.ArgumentParser(
        description="Generate Python Type Stubs for Java classes that are optimized for chaquopy."
    )
    parser.add_argument(
        "prefixes",
        type=str,
        nargs="+",
        help="package prefixes to generate stubs for (e.g. org.myproject)",
    )
    parser.add_argument(
        "--jvmpath",
        type=str,
        help='path to the JVM ("libjvm.so", "jvm.dll", ...) (default: use system default JVM)',
    )
    parser.add_argument(
        "--classpath",
        type=str,
        default=".",
        help='java class path to use, separated by ":". '
        "glob-like expressions (e.g. dir/*.jar) are supported (default: .)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="path to write stubs to (default: .)",
    )
    parser.add_argument(
        "--no-javadoc",
        dest="with_javadoc",
        action="store_false",
        default=True,
        help="do not generate docstrings from JavaDoc where available",
    )

    args = parser.parse_args()

    classpath = [c for c_in in args.classpath.split(":") for c in glob(c_in)]

    log.info("Starting JPype JVM with classpath " + str(classpath))
    jpype.startJVM(jvmpath=args.jvmpath, classpath=classpath)  # noqa: exists
    prefix_packages = [importlib.import_module(prefix) for prefix in args.prefixes]
    generate_java_stubs(
        prefix_packages,  # type: ignore
        output_dir=args.output_dir,
        include_javadoc=args.with_javadoc,
    )

    log.info("Generation done.")
    jpype.java.lang.Runtime.getRuntime().halt(0)
