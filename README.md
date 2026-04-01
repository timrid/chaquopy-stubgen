# chaquopy-stubgen
This tool is a Python type stub generator from Java classes. It is optimized for the usage with Android via [chaquopy v17](https://github.com/chaquo/chaquopy) and [briefcase](https://github.com/beeware/).

The generated stubs can be used with Python 3.10 or higher.

> **⚠️ Disclaimer:** This is **not** an official tool of the [Chaquopy](https://github.com/chaquo/chaquopy) project. It is an independent, community-maintained project.


# CLI Usage
Example call `uv run -m chaquopy_stubgen "$ANDROID_HOME/platforms/android-35/android.jar"`

```
$ uv run -m chaquopy_stubgen --help
usage: __main__.py [-h] [--jvmpath JVMPATH] [--output-dir OUTPUT_DIR] [--no-clean] [--cache-dir CACHE_DIR] inputs [inputs ...]

Generate Python Type Stubs for Java classes that are optimized for chaquopy.

positional arguments:
  inputs                List of .jar/.aar files, directories containing .class files, Android platform shorthands (e.g.
                        'android-35'), or Maven coordinates (e.g. 'androidx.appcompat:appcompat:1.0.2') to generate stubs for.

options:
  -h, --help            show this help message and exit
  --jvmpath JVMPATH     path to the JVM ("libjvm.so", "jvm.dll", ...) (default: use system default JVM)
  --output-dir OUTPUT_DIR
                        path to write stubs to (default: ./dist/stubs)
  --no-clean            skip clearing the output directory before generating stubs
  --cache-dir CACHE_DIR
                        directory for caching downloaded artifacts (default: ~/.cache/chaquopy-stubgen)
```

# Caveats & Limitations
## Importing Java Packages
Always use `from java.lang import String` rather than `import java.lang.String`. While the stubs permit both forms, only the first works at runtime under chaquopy's import hook. See the [chaquopy documentation](https://chaquo.com/chaquopy/doc/current/python.html#import-hook) for details.

## Handling of null Values
In Java, any reference type can in principle be `null`. Annotating every return type as `X | None` would be technically correct, but makes the generated stubs very noisy and forces callers to perform `if ... is not None:` checks everywhere.

Whether a method can actually return `null` usually only becomes apparent from its documentation. chaquopy-stubgen therefore ships a whitelist of methods that are documented to return `null`; those are emitted with `| None` appended to their return type. All other reference return types are treated as non-optional, even though they could theoretically be `null` at runtime.

The whitelist is not exhaustive and may have gaps or false positives. Feel free to open an issue or pull request if you find a missing or incorrect entry.

# Development
- Create venv: `uv sync`
- Test: `uv run pytest`


# Credits
This is based on [stubgenj](https://gitlab.cern.ch/scripting-tools/stubgenj), but generates stubs optimized for `chaquopy` and is internally reworked to use [ASM](https://asm.ow2.io/) instead of Java Reflection.

