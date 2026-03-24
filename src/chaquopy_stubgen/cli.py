import argparse
import logging
import time
from pathlib import Path

from chaquopy_stubgen._artifacts.android import (
    is_android_shorthand,
    resolve_android_jar,
)
from chaquopy_stubgen._artifacts.maven import (
    is_maven_coordinate,
    parse_maven_coordinate,
    resolve_maven_artifact,
)
from chaquopy_stubgen._log import configure_logging
from chaquopy_stubgen._stubgen.main import convert_to_python_stubs

log = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Generate Python Type Stubs for Java classes that are optimized for chaquopy."
    )
    parser.add_argument(
        "inputs",
        type=str,
        nargs="+",
        help=(
            "List of .jar/.aar files, directories containing .class files, "
            "Android platform shorthands (e.g. 'android-35'), "
            "or Maven coordinates (e.g. 'androidx.appcompat:appcompat:1.0.2') to generate stubs for."
        ),
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
        help="path to write stubs to (default: ./dist/stubs)",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        default=False,
        help="skip clearing the output directory before generating stubs",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="directory for caching downloaded artifacts (default: ~/.cache/chaquopy-stubgen)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    cache_dir = Path(args.cache_dir) if args.cache_dir is not None else None
    input_paths: list[Path] = []
    for inp in args.inputs:
        if inp.endswith(".jar") or inp.endswith(".aar"):
            input_paths.append(Path(inp))
        elif is_android_shorthand(inp):
            log.info(f"Resolving Android platform {inp}...")
            input_paths.append(resolve_android_jar(inp, cache_dir=cache_dir))
        elif is_maven_coordinate(inp):
            coord = parse_maven_coordinate(inp)
            log.info(f"Resolving Maven artifact {coord}...")
            input_paths.append(resolve_maven_artifact(coord, cache_dir=cache_dir))
        elif Path(inp).is_dir():
            input_paths.append(Path(inp))
        else:
            parser.error(
                f"Input {inp!r} is neither a .jar/.aar file, a directory containing .class files, "
                "an Android platform shorthand (e.g. 'android-35'), nor a valid Maven coordinate "
                "(expected format: 'groupId:artifactId:version')."
            )

    log.info(f"Generating stubs for {[str(p) for p in input_paths]} to {output_dir}")
    t0 = time.perf_counter()
    convert_to_python_stubs(
        input_paths,
        output_dir,
        jvmpath=args.jvmpath,
        clear_output_dir=not args.no_clean,
    )
    elapsed = time.perf_counter() - t0
    log.info(f"Generation done in {elapsed:.1f}s.")
